"""Catálogo mayorista Q1 — 10 productos por category_id (totales = sales_records)."""
from __future__ import annotations

from typing import Any

from paquetes.tablero import catalogo_modelo as modelo
from paquetes.tablero import catalogo_nombres as nombres

CATALOG_VERSION = 3
_MIN_CATALOG_DOCS = modelo.PRODUCTS_PER_CATEGORY * len(nombres.CATEGORY_BY_ID)


def _row_from_mongo(r: dict[str, Any]) -> dict[str, Any]:
    cid = int(r["category_id"])
    return {
        "product_id": int(r["product_id"]),
        "category_id": cid,
        "line": int(r.get("line") or 0),
        "category": nombres.category_name(cid),
        "name": r["name"],
        "unit_price": float(r.get("unit_price") or 0),
        "unit_cost": float(r.get("unit_cost") or 0),
        "margin_pct": float(r.get("margin_pct") or 0),
        "units": int(r.get("units") or 0),
        "orders": int(r.get("orders") or 0),
        "revenue": float(r.get("revenue") or 0),
    }


def _products_from_mongo(category_id: int) -> list[dict[str, Any]]:
    """Lee solo dim_producto (sin caché) para una categoría."""
    from shared.mongo import get_db

    cid = int(category_id)
    db = get_db()
    rows = list(
        db["dim_producto"]
        .find({"category_id": cid}, {"_id": 0})
        .sort([("line", 1), ("product_id", 1)])
    )
    if len(rows) >= modelo.PRODUCTS_PER_CATEGORY:
        return [_row_from_mongo(r) for r in rows]

    name = nombres.category_name(cid)
    built = modelo.build_products_for_category(cid, name)
    return built


def invalidate_catalog_cache() -> None:
    """Compatibilidad; el catálogo ya no usa caché en memoria."""
    pass


def _product_count_by_category() -> dict[int, int]:
    from shared.mongo import get_db

    db = get_db()
    counts: dict[int, int] = {}
    for row in db["dim_producto"].aggregate(
        [{"$group": {"_id": "$category_id", "n": {"$sum": 1}}}]
    ):
        counts[int(row["_id"])] = int(row["n"])
    return counts


def list_categories() -> dict[str, Any]:
    """12 categorías oficiales (IDs 1–12)."""
    counts = _product_count_by_category()
    rows: list[dict[str, Any]] = []
    for cid in sorted(nombres.CATEGORY_BY_ID.keys()):
        name = nombres.CATEGORY_BY_ID[cid]
        n = counts.get(cid, modelo.PRODUCTS_PER_CATEGORY)
        if n < modelo.PRODUCTS_PER_CATEGORY:
            n = modelo.PRODUCTS_PER_CATEGORY
        rows.append(
            {
                "category_id": cid,
                "name": name,
                "description": modelo.CATEGORY_DESC.get(name, ""),
                "product_count": n,
            }
        )
    return {"catalog_version": CATALOG_VERSION, "items": rows}


def list_products_for_category(
    category_id: int,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Productos de una categoría — siempre desde dim_producto / modelo oficial."""
    limit = max(1, min(limit, 96))
    offset = max(0, offset)
    items = _products_from_mongo(int(category_id))
    total = len(items)
    page = items[offset : offset + limit]

    for p in page:
        p["display_name"] = p.get("name") or p["category"]
        p["wholesale_label"] = f"Cat. {p['category_id']} · SKU {p['product_id']}"

    return {
        "catalog_version": CATALOG_VERSION,
        "category_id": int(category_id),
        "items": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def sync_products_to_mongo() -> dict[str, int]:
    """Escribe 120 productos en dim_producto y dim_categoria."""
    from shared.mongo import get_db

    catalog = modelo.build_full_catalog()
    db = get_db()
    old_images = {
        int(r["product_id"]): r.get("image_url")
        for r in db["dim_producto"].find({"image_url": {"$ne": None}}, {"product_id": 1, "image_url": 1})
    }
    docs = []
    for p in catalog:
        pid = int(p["product_id"])
        docs.append(
            {
                "product_id": pid,
                "name": p["name"],
                "category_id": int(p["category_id"]),
                "line": int(p["line"]),
                "unit_price": p["unit_price"],
                "unit_cost": p["unit_cost"],
                "margin_pct": p["margin_pct"],
                "units": p["units"],
                "orders": p["orders"],
                "revenue": p["revenue"],
                "image_url": old_images.get(pid),
            }
        )

    categorias = []
    for cid in sorted(nombres.CATEGORY_BY_ID.keys()):
        name = nombres.CATEGORY_BY_ID[cid]
        categorias.append(
            {
                "category_id": cid,
                "name": name,
                "description": modelo.CATEGORY_DESC.get(name, ""),
            }
        )

    db["dim_producto"].delete_many({})
    db["dim_categoria"].delete_many({})
    if docs:
        db["dim_producto"].insert_many(docs)
    if categorias:
        db["dim_categoria"].insert_many(categorias)

    from shared.collections_q1 import drop_duplicate_catalog_collections

    drop_duplicate_catalog_collections(db)

    return {"dim_producto": len(docs), "dim_categoria": len(categorias)}
