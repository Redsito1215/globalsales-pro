"""Consultas MongoDB — Cuadrante Q1 (tablero). Capa estratégica: fact_ventas + dims."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any

from shared.data_layers import analytics_fact, landing_sales, strategic_ready
from shared.mongo import get_db, get_read_dw_db, sales_collection

# Caché en memoria (demo)
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SEC = 90.0
_MAX_DATE_CACHE: tuple[float, str | None] | None = None


def _cache_get(key: str) -> Any | None:
    row = _CACHE.get(key)
    if not row:
        return None
    ts, val = row
    if time.monotonic() - ts > _CACHE_TTL_SEC:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: Any) -> Any:
    _CACHE[key] = (time.monotonic(), val)
    return val


def _cache_key(name: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return name + ":" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def clear_query_cache() -> None:
    global _MAX_DATE_CACHE
    _CACHE.clear()
    _MAX_DATE_CACHE = None


def dataset_max_order_date() -> str | None:
    """Fecha máxima de la capa estratégica (fact_ventas.fecha_id)."""
    global _MAX_DATE_CACHE
    now = time.monotonic()
    if _MAX_DATE_CACHE and now - _MAX_DATE_CACHE[0] < 300:
        return _MAX_DATE_CACHE[1]
    val = None
    if strategic_ready():
        doc = analytics_fact().find_one({}, {"fecha_id": 1, "_id": 0}, sort=[("fecha_id", -1)])
        val = (doc or {}).get("fecha_id")
    if not val:
        doc = landing_sales().find_one({}, {"order_date": 1, "_id": 0}, sort=[("order_date", -1)])
        val = (doc or {}).get("order_date")
    if isinstance(val, datetime):
        val = val.strftime("%Y-%m-%d")
    elif val is not None:
        val = str(val)[:10]
    _MAX_DATE_CACHE = (now, val)
    return val


def _fact_match(
    region: str | None = None,
    item_type: str | None = None,
    channel: str | None = None,
    priority: str | None = None,
    months: int | None = None,
) -> dict[str, Any]:
    """Filtros en IDs de fact_ventas (+ fecha_id)."""
    db = get_read_dw_db()
    q: dict[str, Any] = {}
    if region:
        r = db["dim_region"].find_one({"name": region}, {"region_id": 1})
        q["region_id"] = int(r["region_id"]) if r else -1
    if item_type:
        c = db["dim_categoria"].find_one({"name": item_type}, {"category_id": 1})
        q["category_id"] = int(c["category_id"]) if c else -1
    if channel:
        ch = db["dim_canal"].find_one({"name": channel}, {"channel_id": 1})
        q["channel_id"] = int(ch["channel_id"]) if ch else -1
    if priority:
        p = db["dim_prioridad"].find_one(
            {"$or": [{"code": priority}, {"name": priority}]},
            {"priority_id": 1},
        )
        q["priority_id"] = int(p["priority_id"]) if p else -1
    if months and months < 999:
        anchor = dataset_max_order_date() or datetime.utcnow().strftime("%Y-%m-%d")
        try:
            end = datetime.strptime(anchor[:10], "%Y-%m-%d")
        except ValueError:
            end = datetime.utcnow()
        cutoff = (end - timedelta(days=months * 31)).strftime("%Y-%m-%d")
        q["fecha_id"] = {"$gte": cutoff}
    return q


def _landing_match(
    region: str | None = None,
    item_type: str | None = None,
    channel: str | None = None,
    priority: str | None = None,
    months: int | None = None,
) -> dict[str, Any]:
    """Filtros denormalizados sobre sales_records (listados/export)."""
    q: dict[str, Any] = {}
    if region:
        q["region"] = region
    if item_type:
        q["item_type"] = item_type
    if channel:
        q["sales_channel"] = channel
    if priority:
        q["order_priority"] = priority
    if months and months < 999:
        anchor = dataset_max_order_date() or datetime.utcnow().strftime("%Y-%m-%d")
        try:
            end = datetime.strptime(anchor[:10], "%Y-%m-%d")
        except ValueError:
            end = datetime.utcnow()
        cutoff = (end - timedelta(days=months * 31)).strftime("%Y-%m-%d")
        q["order_date"] = {"$gte": cutoff}
    return q


def _prefix(match: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"$match": match}] if match else []


def _empty_summary(**filters) -> dict[str, Any]:
    try:
        max_date = dataset_max_order_date()
    except Exception:
        max_date = None
    return {
        "total_orders": 0,
        "total_revenue": 0.0,
        "total_profit": 0.0,
        "total_cost": 0.0,
        "avg_margin": 0.0,
        "countries": 0,
        "item_types": 0,
        "dataset_max_date": max_date,
        "strategic_ready": False,
        "data_layer": "estrategico",
        "message": "Capa estratégica vacía. Ejecuta Datos → Carga ELT o Construir modelo (fact_ventas).",
    }


def get_summary(**filters) -> dict[str, Any]:
    key = _cache_key("summary", {**filters, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, _empty_summary(**filters))

    match = _fact_match(**filters)
    pipe = _prefix(match) + [
        {
            "$facet": {
                "totals": [
                    {
                        "$group": {
                            "_id": None,
                            "r": {"$sum": "$total_revenue"},
                            "p": {"$sum": "$total_profit"},
                            "co": {"$sum": "$total_cost"},
                            "n": {"$sum": 1},
                        }
                    }
                ],
                "countries": [{"$group": {"_id": "$country_id"}}, {"$count": "n"}],
                "item_types": [{"$group": {"_id": "$category_id"}}, {"$count": "n"}],
            }
        }
    ]
    rows = list(analytics_fact().aggregate(pipe, allowDiskUse=True))
    facet = rows[0] if rows else {}
    x = (facet.get("totals") or [{}])[0] if facet.get("totals") else {}
    rev = float(x.get("r") or 0)
    countries = int(((facet.get("countries") or [{}])[0] or {}).get("n") or 0)
    item_types = int(((facet.get("item_types") or [{}])[0] or {}).get("n") or 0)
    lagging = False
    try:
        from shared.analytics_sync import get_strategic_lag

        lagging = bool(get_strategic_lag().get("strategic_lagging"))
    except Exception:
        pass
    result = {
        "total_orders": int(x.get("n") or 0),
        "total_revenue": round(rev, 2),
        "total_profit": round(float(x.get("p") or 0), 2),
        "total_cost": round(float(x.get("co") or 0), 2),
        "avg_margin": round(float((x.get("p") or 0) / rev * 100) if rev else 0, 2),
        "countries": countries,
        "item_types": item_types,
        "dataset_max_date": dataset_max_order_date(),
        "strategic_ready": True,
        "strategic_lagging": lagging,
        "data_layer": "estrategico",
    }
    return _cache_set(key, result)


def revenue_by_region(**filters):
    key = _cache_key("regions", {**filters, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])
    match = _fact_match(**filters)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$lookup": {
                        "from": "dim_region",
                        "localField": "region_id",
                        "foreignField": "region_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$d.name", "Sin región"]},
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                        "orders": {"$sum": 1},
                    }
                },
                {
                    "$project": {
                        "region": "$_id",
                        "revenue": {"$round": ["$revenue", 2]},
                        "profit": {"$round": ["$profit", 2]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
                {"$sort": {"revenue": -1}},
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows)


def revenue_by_product(**filters):
    key = _cache_key("products", {**filters, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])
    match = _fact_match(**filters)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$lookup": {
                        "from": "dim_categoria",
                        "localField": "category_id",
                        "foreignField": "category_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$d.name", "Sin categoría"]},
                        "units": {"$sum": "$units_sold"},
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                    }
                },
                {
                    "$project": {
                        "item_type": "$_id",
                        "units": 1,
                        "revenue": {"$round": ["$revenue", 2]},
                        "profit": {"$round": ["$profit", 2]},
                        "_id": 0,
                    }
                },
                {"$sort": {"revenue": -1}},
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows)


def monthly_trend(last_n: int = 24, **filters):
    payload = {**filters, "last_n": last_n, "layer": "fact"}
    key = _cache_key("trend", payload)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])

    f = dict(filters)
    if not f.get("months") or int(f.get("months") or 0) >= 999:
        if last_n and last_n < 999:
            f["months"] = last_n
    match = _fact_match(**f)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": {"$substr": ["$fecha_id", 0, 7]},
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                        "orders": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": -1}},
                {"$limit": last_n if last_n < 999 else 120},
                {
                    "$project": {
                        "month": "$_id",
                        "revenue": {"$round": ["$revenue", 2]},
                        "profit": {"$round": ["$profit", 2]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, list(reversed(rows)))


def channel_breakdown(**filters):
    key = _cache_key("channels", {**filters, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])
    match = _fact_match(**filters)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$lookup": {
                        "from": "dim_canal",
                        "localField": "channel_id",
                        "foreignField": "channel_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$d.name", "Sin canal"]},
                        "orders": {"$sum": 1},
                        "revenue": {"$sum": "$total_revenue"},
                    }
                },
                {
                    "$project": {
                        "sales_channel": "$_id",
                        "orders": 1,
                        "revenue": {"$round": ["$revenue", 2]},
                        "_id": 0,
                    }
                },
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows)


def priority_breakdown(**filters):
    key = _cache_key("priorities", {**filters, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])
    match = _fact_match(**filters)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$lookup": {
                        "from": "dim_prioridad",
                        "localField": "priority_id",
                        "foreignField": "priority_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$d.code", "M"]},
                        "orders": {"$sum": 1},
                    }
                },
                {"$project": {"order_priority": "$_id", "orders": 1, "_id": 0}},
                {"$sort": {"order_priority": 1}},
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows)


def top_countries(n: int = 10, **filters):
    key = _cache_key("countries", {**filters, "n": n, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, [])
    match = _fact_match(**filters)
    rows = list(
        analytics_fact().aggregate(
            _prefix(match)
            + [
                {
                    "$lookup": {
                        "from": "dim_pais",
                        "localField": "country_id",
                        "foreignField": "country_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$d.name", "Sin país"]},
                        "revenue": {"$sum": "$total_revenue"},
                        "orders": {"$sum": 1},
                    }
                },
                {"$sort": {"revenue": -1}},
                {"$limit": n},
                {
                    "$project": {
                        "country": "$_id",
                        "revenue": {"$round": ["$revenue", 2]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows)


def search_orders(
    country=None,
    item_type=None,
    channel=None,
    priority=None,
    region=None,
    months=None,
    limit=50,
    offset=0,
):
    """Listado histórico: capa landing (sales_records)."""
    q = _landing_match(region=region, item_type=item_type, channel=channel, priority=priority, months=months)
    if country:
        q["country"] = {"$regex": country, "$options": "i"}
    return list(
        landing_sales()
        .find(q, {"_id": 0})
        .sort("order_date", -1)
        .skip(offset)
        .limit(limit)
    )


def count_orders(**kwargs):
    q = _landing_match(
        region=kwargs.get("region"),
        item_type=kwargs.get("item_type"),
        channel=kwargs.get("channel"),
        priority=kwargs.get("priority"),
        months=kwargs.get("months"),
    )
    if kwargs.get("country"):
        q["country"] = {"$regex": kwargs["country"], "$options": "i"}
    return landing_sales().count_documents(q)


def ping_mongo() -> bool:
    try:
        sales_collection().database.client.admin.command("ping")
        return True
    except Exception:
        return False
