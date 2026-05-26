"""Dashboard GLOBTRADE — lee MongoDB (sales_records) tras el ELT."""
from __future__ import annotations

from typing import Any

from pymongo import MongoClient

from config.settings import settings

def _db():
    return MongoClient(settings.mongo_uri)[settings.mongo_db]

def _col():
    return _db()["sales_records"]

def _collection(name: str):
    return _db()[name]

_TABLE_LABELS: dict[str, str] = {
    "dim_region": "Regiones",
    "dim_pais": "Países",
    "dim_categoria": "Categorías",
    "dim_producto": "Productos",
    "dim_canal": "Canales",
    "dim_prioridad": "Prioridades",
    "dim_cliente": "Clientes",
    "dim_tiempo": "Tiempo",
    # catálogos espejo (siguen siendo maestros; solo lectura)
    "product_categories": "Catálogo (espejo): Categorías",
    "products": "Catálogo (espejo): Productos",
}

_MASTER_ORDER: list[str] = [
    "dim_region",
    "dim_pais",
    "dim_categoria",
    "dim_producto",
    "dim_canal",
    "dim_prioridad",
    "dim_cliente",
    "dim_tiempo",
    "product_categories",
    "products",
]

def master_tables() -> list[dict[str, Any]]:
    db = _db()
    existing = set(db.list_collection_names())
    out: list[dict[str, Any]] = []

    for name in _MASTER_ORDER:
        if name not in existing:
            out.append({"id": name, "label": _TABLE_LABELS.get(name, name), "count": 0})
            continue
        out.append({"id": name, "label": _TABLE_LABELS.get(name, name), "count": db[name].count_documents({})})

    return out

def _parse_q(q: str):
    q = (q or "").strip()
    if not q:
        return None
    try:
        if "." in q:
            return float(q)
        return int(q)
    except ValueError:
        return q

def master_browse(name: str, limit: int = 50, offset: int = 0, q: str = "") -> dict[str, Any]:
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    col = _collection(name)
    sample = col.find_one({}, {"_id": 0}) or {}
    keys = [k for k in sample.keys() if k != "_id"]

    query: dict[str, Any] = {}
    parsed = _parse_q(q)
    if parsed is not None and keys:
        ors: list[dict[str, Any]] = []
        if isinstance(parsed, (int, float)):
            for k in keys:
                ors.append({k: parsed})
        else:
            for k in keys:
                ors.append({k: {"$regex": str(parsed), "$options": "i"}})
        query = {"$or": ors} if ors else {}

    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).skip(offset).limit(limit))
    return {
        "collection": name,
        "label": _TABLE_LABELS.get(name, name),
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": rows,
    }

def get_summary():
    c = _col()
    pipe_rev = list(c.aggregate([{"$group": {"_id": None, "r": {"$sum": "$total_revenue"}, "p": {"$sum": "$total_profit"}, "co": {"$sum": "$total_cost"}, "n": {"$sum": 1}}}]))
    x = pipe_rev[0] if pipe_rev else {}
    rev = x.get("r") or 0
    return {
        "total_orders": c.count_documents({}),
        "total_revenue": round(float(rev), 2),
        "total_profit": round(float(x.get("p") or 0), 2),
        "total_cost": round(float(x.get("co") or 0), 2),
        "avg_margin": round(float((x.get("p") or 0) / rev * 100) if rev else 0, 2),
        "countries": len(c.distinct("country")),
        "item_types": len(c.distinct("item_type")),
    }

def revenue_by_region():
    return list(_col().aggregate([
        {"$group": {"_id": "$region", "revenue": {"$sum": "$total_revenue"}, "profit": {"$sum": "$total_profit"}, "orders": {"$sum": 1}}},
        {"$project": {"region": "$_id", "revenue": {"$round": ["$revenue", 2]}, "profit": {"$round": ["$profit", 2]}, "orders": 1, "_id": 0}},
        {"$sort": {"revenue": -1}},
    ]))

def revenue_by_product():
    return list(_col().aggregate([
        {"$group": {"_id": "$item_type", "units": {"$sum": "$units_sold"}, "revenue": {"$sum": "$total_revenue"}, "profit": {"$sum": "$total_profit"}}},
        {"$project": {"item_type": "$_id", "units": 1, "revenue": {"$round": ["$revenue", 2]}, "profit": {"$round": ["$profit", 2]}, "_id": 0}},
        {"$sort": {"revenue": -1}},
    ]))

def monthly_trend(last_n: int = 24):
    rows = list(_col().aggregate([
        {"$group": {"_id": {"$substr": ["$order_date", 0, 7]}, "revenue": {"$sum": "$total_revenue"}, "profit": {"$sum": "$total_profit"}, "orders": {"$sum": 1}}},
        {"$sort": {"_id": -1}}, {"$limit": last_n},
        {"$project": {"month": "$_id", "revenue": {"$round": ["$revenue", 2]}, "profit": {"$round": ["$profit", 2]}, "orders": 1, "_id": 0}},
    ]))
    return list(reversed(rows))

def channel_breakdown():
    return list(_col().aggregate([
        {"$group": {"_id": "$sales_channel", "orders": {"$sum": 1}, "revenue": {"$sum": "$total_revenue"}}},
        {"$project": {"sales_channel": "$_id", "orders": 1, "revenue": {"$round": ["$revenue", 2]}, "_id": 0}},
    ]))

def priority_breakdown():
    return list(_col().aggregate([
        {"$group": {"_id": "$order_priority", "orders": {"$sum": 1}}},
        {"$project": {"order_priority": "$_id", "orders": 1, "_id": 0}},
        {"$sort": {"order_priority": 1}},
    ]))

def top_countries(n: int = 10):
    return list(_col().aggregate([
        {"$group": {"_id": "$country", "revenue": {"$sum": "$total_revenue"}, "orders": {"$sum": 1}}},
        {"$sort": {"revenue": -1}}, {"$limit": n},
        {"$project": {"country": "$_id", "revenue": {"$round": ["$revenue", 2]}, "orders": 1, "_id": 0}},
    ]))

def search_orders(country=None, item_type=None, channel=None, priority=None, limit=50, offset=0):
    q = {}
    if country: q["country"] = {"$regex": country, "$options": "i"}
    if item_type: q["item_type"] = {"$regex": item_type, "$options": "i"}
    if channel: q["sales_channel"] = channel
    if priority: q["order_priority"] = priority
    return list(_col().find(q, {"_id": 0}).sort("order_date", -1).skip(offset).limit(limit))

def count_orders(**kwargs):
    q = {}
    if kwargs.get("country"): q["country"] = {"$regex": kwargs["country"], "$options": "i"}
    if kwargs.get("item_type"): q["item_type"] = {"$regex": kwargs["item_type"], "$options": "i"}
    if kwargs.get("channel"): q["sales_channel"] = kwargs["channel"]
    if kwargs.get("priority"): q["order_priority"] = kwargs["priority"]
    return _col().count_documents(q)

def get_order(order_id):
    oid = int(order_id) if str(order_id).isdigit() else order_id
    return _col().find_one({"order_id": str(oid)}, {"_id": 0}) or _col().find_one({"order_id": oid}, {"_id": 0})
