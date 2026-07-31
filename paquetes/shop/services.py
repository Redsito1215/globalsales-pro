"""Servicios tienda — modelo y procesos tipo Shopify."""
from __future__ import annotations

import re
import threading
import uuid
from datetime import date, datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db

_sync_lock = threading.Lock()


def _handle(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "item"


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


def ensure_shop_catalog() -> None:
    """Sincroniza una sola vez si falta catálogo (evita carrera entre /collections y /products)."""
    db = get_db()
    if db["collections"].count_documents({}) > 0 and db["products"].count_documents({}) > 0:
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
            "name": "GLOBTRADE Store",
            "currency": "USD",
            "country_default": "United States of America",
            "checkout_note": "Gracias por comprar en GLOBTRADE.",
        }
    )
    counts["shop_settings"] = 1

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
        collections.append(
            {
                "collection_id": cid,
                "title": cat.get("name", f"Collection {cid}"),
                "handle": _handle(cat.get("name", "")),
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
        cat = db["dim_categoria"].find_one({"category_id": p.get("category_id")}, {"name": 1})
        products.append(
            {
                "product_id": pid,
                "title": p.get("name", f"Product {pid}"),
                "vendor_id": 1,
                "status": "active",
                "product_type": cat.get("name") if cat else "General",
                "tags": cat.get("name") if cat else "",
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
        if p.get("image_url"):
            media.append({"media_id": mid, "product_id": pid, "src": p["image_url"], "alt": p.get("name"), "position": 1})
            mid += 1
        inv_items.append({"inventory_item_id": iid, "variant_id": vid, "sku": f"GT-{pid:05d}", "tracked": True})
        inv_levels.append({"level_id": lid, "inventory_item_id": iid, "location": "Main Warehouse", "available": qty, "committed": 0})
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
    if _cleanup_duplicate_collections(db):
        pass
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for row in db["collections"].find({"published": True}, {"_id": 0}).sort("collection_id", 1):
        cid = int(row["collection_id"])
        if cid in seen:
            continue
        seen.add(cid)
        row["product_count"] = db["collection_products"].count_documents({"collection_id": cid})
        rows.append(row)
    return rows


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
    for p in products:
        pid = p["product_id"]
        variant = db["product_variants"].find_one({"product_id": pid}, {"_id": 0})
        p["variant"] = variant
        p["image"] = db["product_media"].find_one({"product_id": pid}, {"_id": 0, "src": 1, "alt": 1})
        if not p.get("image") and db["dim_producto"].find_one({"product_id": pid}, {"image_url": 1}):
            dim = db["dim_producto"].find_one({"product_id": pid}, {"image_url": 1, "name": 1})
            if dim and dim.get("image_url"):
                p["image"] = {"src": dim["image_url"], "alt": dim.get("name")}
    return {"total": total, "products": products}


def create_checkout_from_cart(data: dict[str, Any]) -> dict[str, Any]:
    """Checkout estilo Shopify → también crea purchase_request legacy."""
    from paquetes.ventas import services as ventas

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
        qty = int(item.get("quantity") or 1)
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
    total = max(subtotal - discount_amount, 0.0)

    email = (data.get("email") or data.get("client_email") or "").strip()
    name = (data.get("name") or data.get("client_name") or "Cliente").strip()
    db["checkouts"].insert_one(
        {
            "checkout_id": checkout_id,
            "email": email,
            "status": "open",
            "subtotal": round(subtotal, 2),
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

    country_id = int(data.get("country_id") or 1)
    channel_id = int(data.get("channel_id") or 1)
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
            "total": total,
            "stock_lines": stock_lines,
        }
    )
    db["checkouts"].update_one({"checkout_id": checkout_id}, {"$set": {"status": "submitted", "request_id": req.get("request_id")}})
    return {
        "checkout_id": checkout_id,
        "subtotal": round(subtotal, 2),
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
