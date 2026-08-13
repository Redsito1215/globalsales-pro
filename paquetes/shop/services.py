"""Servicios tienda — modelo y procesos tipo Shopify."""
from __future__ import annotations

import hashlib
import re
import threading
import uuid
from datetime import date, datetime, timezone
from typing import Any

from paquetes.tablero import catalogo_nombres as nom
from shared.audit import log_audit
from shared.mongo import get_db
from shared.warehouse import DEFAULT_WAREHOUSE_NAME, ensure_default_warehouse, warehouse_summary

_CATEGORY_WEIGHT_KG: dict[str, tuple[float, float]] = {
    "Baby Food": (0.12, 0.45),
    "Beverages": (0.35, 2.0),
    "Cereal": (0.25, 1.5),
    "Clothes": (0.15, 0.9),
    "Cosmetics": (0.05, 0.35),
    "Fruits": (0.08, 1.2),
    "Household": (0.2, 4.5),
    "Meat": (0.25, 1.8),
    "Office Supplies": (0.05, 2.5),
    "Personal Care": (0.08, 0.6),
    "Snacks": (0.05, 0.8),
    "Vegetables": (0.1, 1.5),
}

_sync_lock = threading.Lock()


def _handle(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "item"


def _product_image_src(dim: dict[str, Any] | None, product_id: int, title: str = "") -> str | None:
    """URL de imagen: upload en maestros > archivo local /static/img/products/{id}.jpg."""
    from paquetes.tablero.catalogo_imagenes import resolve_image_url

    name = (dim or {}).get("name") or title or ""
    preserved = (dim or {}).get("image_url")
    return resolve_image_url(int(product_id), name, preserved)


def backfill_product_images(db) -> int:
    """Rellena image_url y product_media desde archivos locales del catálogo."""
    updated = 0
    media_missing = 0
    next_media = _next_id(db["product_media"], "media_id")
    for p in db["dim_producto"].find({}, {"_id": 0, "product_id": 1, "name": 1, "image_url": 1}):
        pid = int(p["product_id"])
        url = _product_image_src(p, pid)
        if not url:
            continue
        if p.get("image_url") != url:
            db["dim_producto"].update_one(
                {"product_id": pid},
                {"$set": {"image_url": url, "image_source": "local_catalog"}},
            )
            updated += 1
        row = db["product_media"].find_one({"product_id": pid}, {"media_id": 1, "src": 1})
        if not row or row.get("src") != url:
            if row:
                db["product_media"].update_one({"product_id": pid}, {"$set": {"src": url, "alt": p.get("name")}})
            else:
                db["product_media"].insert_one(
                    {
                        "media_id": next_media,
                        "product_id": pid,
                        "src": url,
                        "alt": p.get("name"),
                        "position": 1,
                    }
                )
                next_media += 1
            media_missing += 1
    return updated + media_missing


def _cleanup_duplicate_collections(db) -> int:
    """Elimina duplicados legacy por collection_id (de carreras de sync)."""
    removed = 0
    for group in db["collections"].aggregate(
        [
            {"$group": {"_id": "$collection_id", "ids": {"$push": "$_id"}, "n": {"$sum": 1}}},
            {"$match": {"n": {"$gt": 1}}},
        ]
    ):
        dup_ids = sorted(group["ids"])[1:]
        if dup_ids:
            db["collections"].delete_many({"_id": {"$in": dup_ids}})
            removed += len(dup_ids)
    return removed


def _next_id(col, pk: str) -> int:
    row = col.find_one({}, {pk: 1, "_id": 0}, sort=[(pk, -1)])
    return int(row[pk]) + 1 if row and row.get(pk) is not None else 1


def _master_category_map(db) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for cat in db["dim_categoria"].find({}, {"_id": 0}):
        if cat.get("category_id") is None:
            continue
        out[int(cat["category_id"])] = cat
    return out


def _product_counts_by_category(db) -> dict[int, int]:
    counts: dict[int, int] = {}
    for row in db["dim_producto"].aggregate(
        [{"$group": {"_id": "$category_id", "n": {"$sum": 1}}}],
        allowDiskUse=False,
    ):
        if row.get("_id") is None:
            continue
        counts[int(row["_id"])] = int(row["n"])
    return counts


def _collection_display_title(category_id: int) -> str:
    return nom.category_display_name(int(category_id))


def _collections_out_of_sync(db) -> bool:
    masters = _master_category_map(db)
    ops_ids = {int(r["collection_id"]) for r in db["collections"].find({}, {"collection_id": 1})}
    if ops_ids != set(masters.keys()):
        return True
    for row in db["collections"].find({}, {"collection_id": 1, "title": 1}):
        cid = int(row["collection_id"])
        if masters.get(cid) and row.get("title") != _collection_display_title(cid):
            return True
    return False


def _apply_spanish_shop_labels(db) -> None:
    """Actualiza títulos de vitrina sin regenerar inventario ni borrar pedidos."""
    for cat in db["dim_categoria"].find({}, {"category_id": 1}):
        cid = int(cat["category_id"])
        title = _collection_display_title(cid)
        db["collections"].update_many(
            {"collection_id": cid},
            {"$set": {"title": title, "handle": _handle(title)}},
        )
    for p in db["dim_producto"].find({}, {"product_id": 1, "name": 1, "category_id": 1}):
        pid = int(p["product_id"])
        name = nom.product_display_name_by_id(pid, p.get("name", ""))
        if not name:
            continue
        cid = int(p.get("category_id") or 0)
        cat_label = _collection_display_title(cid) if cid else "General"
        db["products"].update_one(
            {"product_id": pid},
            {"$set": {"title": name, "product_type": cat_label}},
        )
        db["product_media"].update_many({"product_id": pid}, {"$set": {"alt": name}})


def _catalog_needs_product_sync(db) -> bool:
    return db["dim_producto"].count_documents({}) != db["products"].count_documents({})


def reconcile_collections_with_masters(db) -> dict[str, int]:
    """Alinea colecciones de vitrina con dim_categoria (elimina huérfanas como categorías borradas)."""
    masters = _master_category_map(db)
    master_ids = set(masters.keys())
    removed = 0
    for row in list(db["collections"].find({}, {"collection_id": 1, "_id": 1})):
        cid = int(row["collection_id"])
        if cid not in master_ids:
            db["collections"].delete_one({"_id": row["_id"]})
            db["collection_products"].delete_many({"collection_id": cid})
            removed += 1

    existing: set[int] = set()
    for row in db["collections"].find({}, {"collection_id": 1, "_id": 1, "title": 1}):
        cid = int(row["collection_id"])
        existing.add(cid)
        cat = masters[cid]
        title = _collection_display_title(cid)
        db["collections"].update_one(
            {"_id": row["_id"]},
            {
                "$set": {
                    "title": title,
                    "handle": _handle(title),
                    "description": cat.get("description", ""),
                    "published": True,
                }
            },
        )

    added = 0
    for cid in sorted(master_ids - existing):
        cat = masters[cid]
        title = _collection_display_title(cid)
        db["collections"].insert_one(
            {
                "collection_id": cid,
                "title": title,
                "handle": _handle(title),
                "description": cat.get("description", ""),
                "published": True,
            }
        )
        added += 1

    db["collection_products"].delete_many({})
    cp_links: list[dict[str, Any]] = []
    cp_id = 1
    for cid in sorted(master_ids):
        pos = 1
        for prod in db["dim_producto"].find({"category_id": cid}, {"product_id": 1}):
            cp_links.append(
                {
                    "id": cp_id,
                    "collection_id": cid,
                    "product_id": int(prod["product_id"]),
                    "position": pos,
                }
            )
            cp_id += 1
            pos += 1
    if cp_links:
        db["collection_products"].insert_many(cp_links)

    return {
        "collections_removed": removed,
        "collections_added": added,
        "collection_products": len(cp_links),
    }


def ensure_shop_catalog() -> None:
    """Sincroniza catálogo si falta o si colecciones/productos no coinciden con maestros."""
    db = get_db()
    has_catalog = db["collections"].count_documents({}) > 0 and db["products"].count_documents({}) > 0
    if has_catalog:
        needs_reconcile = _collections_out_of_sync(db)
        needs_products = _catalog_needs_product_sync(db)
        needs_images = db["product_media"].count_documents({}) < db["dim_producto"].count_documents({})
        if needs_reconcile or needs_products or needs_images:
            with _sync_lock:
                if _collections_out_of_sync(db):
                    reconcile_collections_with_masters(db)
                if needs_images:
                    backfill_product_images(db)
                if _catalog_needs_product_sync(db):
                    _sync_from_masters_unlocked()
                else:
                    _apply_spanish_shop_labels(db)
        else:
            _apply_spanish_shop_labels(db)
        return
    with _sync_lock:
        if db["collections"].count_documents({}) > 0 and db["products"].count_documents({}) > 0:
            return
        _sync_from_masters_unlocked()


def sync_from_masters(*, reset_stock: bool = False) -> dict[str, int]:
    """Sincroniza dim_* → tablas comerciales Shopify.

    Por defecto conserva el stock actual de variantes existentes (no wipe ciego).
    Usa reset_stock=True solo cuando se quiere regenerar inventario desde maestros.
    """
    with _sync_lock:
        return _sync_from_masters_unlocked(reset_stock=reset_stock)


def _sync_from_masters_unlocked(*, reset_stock: bool = False) -> dict[str, int]:
    db = get_db()
    counts: dict[str, int] = {}

    from shared.retail_pricing import patch_dim_producto_prices

    counts["dim_producto_prices_patched"] = patch_dim_producto_prices(db)

    # Conservar stock previo por product_id antes de regenerar catálogo
    previous_stock: dict[int, int] = {}
    if not reset_stock:
        for v in db["product_variants"].find({}, {"product_id": 1, "inventory_quantity": 1}):
            try:
                previous_stock[int(v["product_id"])] = int(v.get("inventory_quantity") or 0)
            except (TypeError, ValueError, KeyError):
                continue

    db["shop_settings"].delete_many({})
    db["shop_settings"].insert_one(
        {
            "shop_id": 1,
            "name": "Tienda GLOBTRADE",
            "currency": "USD",
            "country_default": "United States of America",
            "checkout_note": "Gracias por comprar en GLOBTRADE.",
        }
    )
    counts["shop_settings"] = 1
    ensure_default_warehouse()

    # Conservar proveedores custom; solo asegurar el proveedor por defecto
    if db["vendors"].count_documents({}) == 0:
        db["vendors"].insert_one(
            {
                "vendor_id": 1,
                "name": "GLOBTRADE Supply",
                "email": "supply@globtrade.com",
                "country": "Global",
                "active": True,
            }
        )
    elif not db["vendors"].find_one({"vendor_id": 1}):
        db["vendors"].insert_one(
            {
                "vendor_id": 1,
                "name": "GLOBTRADE Supply",
                "email": "supply@globtrade.com",
                "country": "Global",
                "active": True,
            }
        )
    counts["vendors"] = db["vendors"].count_documents({})

    db["collections"].delete_many({})
    db["collection_products"].delete_many({})
    collections = []
    cp_links = []
    cp_id = 1
    for cat in db["dim_categoria"].find({}, {"_id": 0}).sort("category_id", 1):
        cid = int(cat["category_id"])
        title = _collection_display_title(cid)
        collections.append(
            {
                "collection_id": cid,
                "title": title,
                "handle": _handle(title),
                "description": cat.get("description", ""),
                "published": True,
            }
        )
        pos = 1
        for prod in db["dim_producto"].find({"category_id": cid}, {"product_id": 1}):
            cp_links.append({"id": cp_id, "collection_id": cid, "product_id": int(prod["product_id"]), "position": pos})
            cp_id += 1
            pos += 1
    if collections:
        db["collections"].insert_many(collections)
    if cp_links:
        db["collection_products"].insert_many(cp_links)
    counts["collections"] = len(collections)
    counts["collection_products"] = len(cp_links)

    db["products"].delete_many({})
    db["product_variants"].delete_many({})
    db["product_media"].delete_many({})
    db["inventory_items"].delete_many({})
    db["inventory_levels"].delete_many({})
    products, variants, media, inv_items, inv_levels = [], [], [], [], []
    vid = iid = mid = lid = 1
    for p in db["dim_producto"].find({}, {"_id": 0}).sort("product_id", 1):
        pid = int(p["product_id"])
        cid = int(p.get("category_id") or 0)
        cat_label = _collection_display_title(cid) if cid else "General"
        title = nom.product_display_name_by_id(pid, p.get("name", f"Producto {pid}"))
        products.append(
            {
                "product_id": pid,
                "title": title,
                "vendor_id": 1,
                "status": "active",
                "product_type": cat_label,
                "tags": cat_label,
            }
        )
        price = float(p.get("unit_price") or 0)
        cost = float(p.get("unit_cost") or 0)
        default_qty = int(p.get("units") or 100)
        qty = previous_stock.get(pid, default_qty) if not reset_stock else default_qty
        variants.append(
            {
                "variant_id": vid,
                "product_id": pid,
                "sku": f"GT-{pid:05d}",
                "price": price,
                "compare_at_price": round(price * 1.15, 2) if price else 0,
                "cost": cost,
                "inventory_quantity": qty,
            }
        )
        img_url = _product_image_src(p, pid, title)
        if img_url:
            media.append({"media_id": mid, "product_id": pid, "src": img_url, "alt": title, "position": 1})
            mid += 1
            if not p.get("image_url"):
                db["dim_producto"].update_one(
                    {"product_id": pid},
                    {"$set": {"image_url": img_url, "image_source": "local_catalog"}},
                )
        inv_items.append({"inventory_item_id": iid, "variant_id": vid, "sku": f"GT-{pid:05d}", "tracked": True})
        inv_levels.append({"level_id": lid, "inventory_item_id": iid, "location": DEFAULT_WAREHOUSE_NAME, "available": qty, "committed": 0})
        vid += 1
        iid += 1
        lid += 1
    if products:
        db["products"].insert_many(products)
    if variants:
        db["product_variants"].insert_many(variants)
    if media:
        db["product_media"].insert_many(media)
    if inv_items:
        db["inventory_items"].insert_many(inv_items)
    if inv_levels:
        db["inventory_levels"].insert_many(inv_levels)
    counts["products"] = len(products)
    counts["product_variants"] = len(variants)
    counts["product_media"] = len(media)
    counts["inventory_items"] = len(inv_items)
    counts["stock_preserved"] = 0 if reset_stock else len(previous_stock)

    db["customers"].delete_many({})
    db["customer_addresses"].delete_many({})
    customers, addresses = [], []
    aid = 1
    for c in db["dim_cliente"].find({}, {"_id": 0}).limit(500):
        cid = int(c.get("client_id", aid))
        name = (c.get("name") or f"Customer {cid}").split(" ", 1)
        customers.append(
            {
                "customer_id": cid,
                "email": c.get("email") or f"customer{cid}@globtrade.com",
                "first_name": name[0],
                "last_name": name[1] if len(name) > 1 else "",
                "phone": c.get("phone"),
                "orders_count": 0,
                "total_spent": 0.0,
            }
        )
        pais = db["dim_pais"].find_one({"country_id": c.get("country_id")}, {"name": 1})
        addresses.append(
            {
                "address_id": aid,
                "customer_id": cid,
                "country": pais.get("name") if pais else "Unknown",
                "city": "",
                "address1": "",
                "zip": "",
                "default": True,
            }
        )
        aid += 1
    if customers:
        db["customers"].insert_many(customers)
    if addresses:
        db["customer_addresses"].insert_many(addresses)
    counts["customers"] = len(customers)

    if db["discount_codes"].count_documents({}) == 0:
        db["discount_codes"].insert_one(
            {
                "discount_id": 1,
                "code": "WELCOME10",
                "value_type": "percentage",
                "value": 10,
                "usage_limit": 100,
                "usage_count": 0,
                "active": True,
            }
        )
        db["discount_codes"].insert_one(
            {
                "discount_id": 2,
                "code": "GLOBTRADE50",
                "value_type": "fixed",
                "value": 50,
                "usage_limit": 20,
                "usage_count": 0,
                "active": True,
            }
        )
    counts["discount_codes"] = db["discount_codes"].count_documents({})

    log_audit("shop_sync", entity="shop", details=counts)
    return counts


def list_collections_public() -> list[dict[str, Any]]:
    ensure_shop_catalog()
    db = get_db()
    if _cleanup_duplicate_collections(db) or _collections_out_of_sync(db):
        with _sync_lock:
            reconcile_collections_with_masters(db)
    masters = _master_category_map(db)
    counts = _product_counts_by_category(db)
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for row in db["collections"].find({"published": True}, {"_id": 0}).sort("collection_id", 1):
        cid = int(row["collection_id"])
        if cid in seen or cid not in masters:
            continue
        seen.add(cid)
        row["title"] = _collection_display_title(cid)
        row["product_count"] = counts.get(cid, 0)
        rows.append(row)
    return rows


def _derive_product_specs(dim: dict[str, Any], category_name: str, category_desc: str) -> dict[str, Any]:
    from paquetes.tablero.catalogo_modelo import CATEGORY_DESC

    pid = int(dim.get("product_id") or 0)
    line = int(dim.get("line") or 1)
    stored_weight = dim.get("weight_kg")
    if stored_weight not in (None, ""):
        weight_kg = round(float(stored_weight), 2)
    else:
        lo, hi = _CATEGORY_WEIGHT_KG.get(category_name, (0.15, 3.0))
        h = hashlib.md5(f"{pid}:{line}".encode()).hexdigest()
        frac = int(h[:8], 16) / 0xFFFFFFFF
        weight_kg = round(lo + (hi - lo) * frac, 2)

    main_function = (dim.get("main_function") or "").strip()
    if not main_function:
        desc = category_desc or CATEGORY_DESC.get(category_name, category_name)
        main_function = f"{desc}. Variante de línea {line} para venta y distribución B2B."

    description = (dim.get("description") or "").strip()

    return {
        "weight_kg": weight_kg,
        "main_function": main_function,
        "description": description or None,
    }


def _enrich_shop_products(db, products: list[dict[str, Any]]) -> None:
    """Añade variante, imagen, proveedor y ficha comercial al listado de vitrina."""
    if not products:
        return
    pids = [int(p["product_id"]) for p in products]
    variants = {
        int(v["product_id"]): v
        for v in db["product_variants"].find({"product_id": {"$in": pids}}, {"_id": 0})
    }
    media = {
        int(m["product_id"]): m
        for m in db["product_media"].find(
            {"product_id": {"$in": pids}},
            {"_id": 0, "product_id": 1, "src": 1, "alt": 1},
        )
        if m.get("product_id") is not None
    }
    dims = {
        int(d["product_id"]): d
        for d in db["dim_producto"].find({"product_id": {"$in": pids}}, {"_id": 0})
    }
    cat_ids = {int(d["category_id"]) for d in dims.values() if d.get("category_id") is not None}
    cats: dict[int, dict[str, Any]] = {}
    if cat_ids:
        cats = {
            int(c["category_id"]): c
            for c in db["dim_categoria"].find(
                {"category_id": {"$in": list(cat_ids)}},
                {"_id": 0, "category_id": 1, "name": 1, "description": 1},
            )
        }
    vendor_ids = {int(p["vendor_id"]) for p in products if p.get("vendor_id") is not None}
    vendors: dict[int, dict[str, Any]] = {}
    if vendor_ids:
        vendors = {
            int(v["vendor_id"]): v
            for v in db["vendors"].find(
                {"vendor_id": {"$in": list(vendor_ids)}},
                {"_id": 0, "vendor_id": 1, "name": 1, "country": 1, "region_name": 1},
            )
        }
    cp_rows = list(db["collection_products"].find({"product_id": {"$in": pids}}, {"product_id": 1, "collection_id": 1}))
    col_ids = {int(r["collection_id"]) for r in cp_rows if r.get("collection_id") is not None}
    collections: dict[int, dict[str, Any]] = {}
    if col_ids:
        collections = {
            int(c["collection_id"]): c
            for c in db["collections"].find(
                {"collection_id": {"$in": list(col_ids)}},
                {"_id": 0, "collection_id": 1, "title": 1},
            )
        }
    cp_map = {int(r["product_id"]): int(r["collection_id"]) for r in cp_rows if r.get("collection_id") is not None}
    wh_name = DEFAULT_WAREHOUSE_NAME
    try:
        wh_name = warehouse_summary()["name"]
    except Exception:
        pass

    for p in products:
        pid = int(p["product_id"])
        dim = dims.get(pid, {})
        if not dim.get("product_id"):
            dim = {**dim, "product_id": pid, "name": dim.get("name") or p.get("title")}
        variant = variants.get(pid)
        p["variant"] = variant
        image = media.get(pid)
        img_src = _product_image_src(dim, pid, p.get("title", ""))
        if not image and img_src:
            image = {"src": img_src, "alt": dim.get("name") or p.get("title")}
        p["image"] = image

        cid = int(dim.get("category_id") or 0)
        cat = cats.get(cid, {})
        category_key = cat.get("name") or (nom.category_name(cid) if cid else p.get("product_type") or "")
        category_name = _collection_display_title(cid) if cid else (p.get("product_type") or "General")
        category_desc = cat.get("description") or ""
        specs = _derive_product_specs(dim, category_key, category_desc)

        vendor = vendors.get(int(p.get("vendor_id") or 0), {})
        vendor_geo = " · ".join(x for x in [vendor.get("region_name"), vendor.get("country")] if x)
        col_id = cp_map.get(pid)
        collection = collections.get(col_id) if col_id else None

        margin_pct = dim.get("margin_pct")
        if margin_pct is None and variant:
            price = float(variant.get("price") or 0)
            cost = float(variant.get("cost") or 0)
            if price > 0:
                margin_pct = round((price - cost) / price * 100, 1)

        spanish_title = nom.product_display_name_by_id(pid, p.get("title") or dim.get("name") or "")
        p["title"] = spanish_title
        p["name"] = spanish_title
        p["product_type"] = category_name
        if p.get("image"):
            p["image"]["alt"] = spanish_title
        p["category_name"] = category_name
        p["category_description"] = category_desc
        p["collection_title"] = _collection_display_title(col_id) if col_id else (collection or {}).get("title")
        p["vendor_name"] = vendor.get("name") or "GLOBTRADE Supply"
        p["vendor_location"] = vendor_geo or None
        p["warehouse"] = wh_name
        p["line"] = dim.get("line")
        p["margin_pct"] = margin_pct
        p["unit_price"] = float((variant or {}).get("price") or dim.get("unit_price") or 0)
        p["unit_cost"] = float((variant or {}).get("cost") or dim.get("unit_cost") or 0)
        p.update(specs)


def list_products_shop(*, collection_id: int | None = None, limit: int = 48, offset: int = 0) -> dict[str, Any]:
    ensure_shop_catalog()
    db = get_db()
    product_ids = None
    if collection_id:
        product_ids = [
            x["product_id"]
            for x in db["collection_products"].find({"collection_id": int(collection_id)}, {"product_id": 1})
        ]
    query: dict[str, Any] = {"status": "active"}
    if product_ids is not None:
        query["product_id"] = {"$in": product_ids or [-1]}
    col = db["products"]
    total = col.count_documents(query)
    products = list(col.find(query, {"_id": 0}).sort("product_id", 1).skip(offset).limit(limit))
    _enrich_shop_products(db, products)
    return {"total": total, "products": products}


def get_product_shop(product_id: int) -> dict[str, Any] | None:
    """Ficha comercial de un producto para la vitrina."""
    ensure_shop_catalog()
    db = get_db()
    product = db["products"].find_one({"product_id": int(product_id)}, {"_id": 0})
    if not product:
        return None
    _enrich_shop_products(db, [product])
    return product


def quote_shipping(data: dict[str, Any]) -> dict[str, Any]:
    from shared.shipping_rates import shipping_quote

    db = get_db()
    country_id = int(data.get("country_id") or 0)
    if country_id < 1:
        raise ValueError("invalid_country")
    lines = data.get("lines") or []
    if not lines:
        raise ValueError("lines_required")
    quote = shipping_quote(db, country_id=country_id, lines=lines)
    return {"status": "ok", **quote}


def create_checkout_from_cart(data: dict[str, Any]) -> dict[str, Any]:
    """Checkout estilo Shopify → también crea purchase_request legacy."""
    from paquetes.ventas import services as ventas
    from shared.shipping_rates import is_online_channel, shipping_quote

    db = get_db()
    lines_in = data.get("lines") or []
    if not lines_in:
        raise ValueError("lines_required")

    checkout_id = _next_id(db["checkouts"], "checkout_id")
    subtotal = 0.0
    line_docs = []
    lid = _next_id(db["checkout_line_items"], "line_id")
    pr_lines = []
    for item in lines_in:
        vid = int(item.get("variant_id") or item.get("product_id") or 0)
        try:
            qty = int(item.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty < 1:
            raise ValueError("invalid_quantity")
        variant = db["product_variants"].find_one({"variant_id": vid}) or db["product_variants"].find_one({"product_id": vid})
        if not variant:
            raise ValueError("invalid_variant")
        available = int(variant.get("inventory_quantity") or 0)
        if available < qty:
            raise ValueError("insufficient_stock")
        price = float(variant.get("price") or 0)
        subtotal += price * qty
        line_docs.append({"line_id": lid, "checkout_id": checkout_id, "variant_id": variant["variant_id"], "quantity": qty, "price": price})
        pr_lines.append(
            {
                "product_id": int(variant["product_id"]),
                "quantity": qty,
                "unit_price": price,
                "variant_id": int(variant["variant_id"]),
                "unit_cost": float(variant.get("cost") or 0),
            }
        )
        lid += 1

    discount_code = (data.get("discount_code") or "").strip().upper()
    discount_amount = 0.0
    if discount_code:
        discount_amount, _coupon = _apply_coupon(db, discount_code, subtotal)

    country_id = int(data.get("country_id") or 1)
    channel_id = int(data.get("channel_id") or 1)
    shipping_cost = 0.0
    shipping_destination = (data.get("shipping_destination") or data.get("destination") or "").strip() or None
    shipping_region = None
    if is_online_channel(db, channel_id):
        if not shipping_destination:
            raise ValueError("destination_required")
        quote = shipping_quote(db, country_id=country_id, lines=lines_in)
        shipping_cost = float(quote.get("shipping_cost") or 0)
        shipping_region = quote.get("region_name")

    total = max(subtotal - discount_amount + shipping_cost, 0.0)

    email = (data.get("email") or data.get("client_email") or "").strip()
    name = (data.get("name") or data.get("client_name") or "Cliente").strip()
    db["checkouts"].insert_one(
        {
            "checkout_id": checkout_id,
            "email": email,
            "status": "open",
            "subtotal": round(subtotal, 2),
            "shipping_cost": round(shipping_cost, 2),
            "discount_code": discount_code or None,
            "discount_amount": round(discount_amount, 2),
            "total_price": round(total, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if line_docs:
        db["checkout_line_items"].insert_many(line_docs)

    stock_lines: list[dict[str, Any]] = []
    for item in lines_in:
        vid = int(item.get("variant_id") or item.get("product_id") or 0)
        qty = int(item.get("quantity") or 1)
        variant = db["product_variants"].find_one({"variant_id": vid}) or db["product_variants"].find_one({"product_id": vid})
        if variant:
            stock_lines.append({"variant_id": int(variant["variant_id"]), "quantity": qty})
        _deduct_stock(db, vid, qty)

    if discount_code:
        db["discount_codes"].update_one({"code": discount_code}, {"$inc": {"usage_count": 1}})

    req = ventas.create_request(
        {
            "client_name": name,
            "client_email": email,
            "client_phone": data.get("phone"),
            "country_id": country_id,
            "channel_id": channel_id,
            "notes": data.get("notes"),
            "lines": pr_lines,
            "discount_code": discount_code,
            "discount_amount": discount_amount,
            "subtotal": subtotal,
            "shipping_cost": shipping_cost,
            "shipping_destination": shipping_destination,
            "shipping_region": shipping_region,
            "total": total,
            "stock_lines": stock_lines,
        }
    )
    db["checkouts"].update_one({"checkout_id": checkout_id}, {"$set": {"status": "submitted", "request_id": req.get("request_id")}})
    return {
        "checkout_id": checkout_id,
        "subtotal": round(subtotal, 2),
        "shipping_cost": round(shipping_cost, 2),
        "discount_amount": round(discount_amount, 2),
        "total_price": round(total, 2),
        "request": req,
    }


def _apply_coupon(db, code: str, subtotal: float) -> tuple[float, dict]:
    doc = db["discount_codes"].find_one({"code": code, "active": True})
    if not doc:
        raise ValueError("invalid_coupon")
    used = int(doc.get("usage_count") or 0)
    limit = int(doc.get("usage_limit") or 0)
    if limit and used >= limit:
        raise ValueError("coupon_exhausted")
    if doc.get("value_type") == "percentage":
        amount = round(subtotal * float(doc.get("value") or 0) / 100.0, 2)
    else:
        amount = round(float(doc.get("value") or 0), 2)
    return min(amount, subtotal), doc


def _deduct_stock(db, variant_id: int, qty: int) -> None:
    variant = db["product_variants"].find_one({"variant_id": variant_id}) or db["product_variants"].find_one({"product_id": variant_id})
    if not variant:
        return
    vid = int(variant["variant_id"])
    new_qty = max(int(variant.get("inventory_quantity") or 0) - qty, 0)
    db["product_variants"].update_one({"variant_id": vid}, {"$set": {"inventory_quantity": new_qty}})
    inv = db["inventory_items"].find_one({"variant_id": vid})
    if inv:
        db["inventory_levels"].update_one(
            {"inventory_item_id": inv["inventory_item_id"]},
            {"$inc": {"available": -qty, "committed": qty}},
        )


def restock(db, variant_id: int, qty: int) -> None:
    """Devuelve unidades al inventario (rechazo / cancelación)."""
    if qty < 1:
        return
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        variant = db["product_variants"].find_one({"product_id": int(variant_id)})
    if not variant:
        return
    vid = int(variant["variant_id"])
    db["product_variants"].update_one(
        {"variant_id": vid},
        {"$inc": {"inventory_quantity": int(qty)}},
    )
    inv = db["inventory_items"].find_one({"variant_id": vid})
    if inv:
        db["inventory_levels"].update_one(
            {"inventory_item_id": inv["inventory_item_id"]},
            {"$inc": {"available": int(qty), "committed": -int(qty)}},
        )


def restock_lines(stock_lines: list[dict[str, Any]] | None) -> None:
    db = get_db()
    for line in stock_lines or []:
        restock(db, int(line.get("variant_id") or 0), int(line.get("quantity") or 0))


def finalize_committed(stock_lines: list[dict[str, Any]] | None) -> None:
    """Al convertir/vender: libera committed (available ya se bajó en checkout)."""
    db = get_db()
    for line in stock_lines or []:
        qty = int(line.get("quantity") or 0)
        if qty < 1:
            continue
        vid = int(line.get("variant_id") or 0)
        variant = db["product_variants"].find_one({"variant_id": vid})
        if not variant:
            continue
        inv = db["inventory_items"].find_one({"variant_id": int(variant["variant_id"])})
        if not inv:
            continue
        level = db["inventory_levels"].find_one({"inventory_item_id": inv["inventory_item_id"]})
        committed = int((level or {}).get("committed") or 0)
        dec = min(qty, committed)
        if dec > 0:
            db["inventory_levels"].update_one(
                {"inventory_item_id": inv["inventory_item_id"]},
                {"$inc": {"committed": -dec}},
            )


def adjust_variant_stock(variant_id: int, available: int) -> dict[str, Any]:
    """Ajuste manual de stock (admin) sin regenerar catálogo."""
    db = get_db()
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        raise ValueError("invalid_variant")
    qty = max(int(available), 0)
    vid = int(variant["variant_id"])
    db["product_variants"].update_one({"variant_id": vid}, {"$set": {"inventory_quantity": qty}})
    inv = db["inventory_items"].find_one({"variant_id": vid})
    if inv:
        db["inventory_levels"].update_one(
            {"inventory_item_id": inv["inventory_item_id"]},
            {"$set": {"available": qty, "committed": 0}},
        )
    log_audit("adjust_stock", entity="product_variants", entity_id=vid, details={"available": qty})
    return {"variant_id": vid, "inventory_quantity": qty}


def validate_coupon(code: str, subtotal: float) -> dict[str, Any]:
    db = get_db()
    amount, doc = _apply_coupon(db, (code or "").strip().upper(), float(subtotal or 0))
    return {
        "code": doc["code"],
        "value_type": doc.get("value_type"),
        "value": doc.get("value"),
        "discount_amount": amount,
        "total": max(float(subtotal or 0) - amount, 0),
    }


def shop_table_counts() -> dict[str, int]:
    db = get_db()
    out = {}
    from shared.shopify_registry import SHOPIFY_TABLES

    for name in SHOPIFY_TABLES:
        try:
            out[name] = db[name].count_documents({})
        except Exception:
            out[name] = 0
    return out
