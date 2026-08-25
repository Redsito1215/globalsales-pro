"""Consultas MongoDB — Cuadrante Q1 (tablero). Capa estratégica: fact_ventas + dims."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from shared.data_layers import analytics_fact, landing_sales, strategic_ready
from shared.mongo import get_db, get_read_dw_db, sales_collection

# Caché en memoria del tablero (TTL corto)
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SEC = 300.0
_DIM_NAME_CACHE: dict[str, tuple[float, dict[str, int]]] = {}
_DIM_CACHE_TTL_SEC = 600.0
_MAX_DATE_CACHE: tuple[float, str | None] | None = None
_FILTER_ANCHOR_CACHE: tuple[float, str | None] | None = None
_FACT_HAS_DATA_CACHE: tuple[float, bool] | None = None
_FACT_GEN_CACHE: tuple[float, int] | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_today_str() -> str:
    return _utc_now().strftime("%Y-%m-%d")


def _fact_gen() -> int:
    """Tamaño aproximado de fact_ventas; invalida caché del tablero al crecer el DW."""
    global _FACT_GEN_CACHE
    now = time.monotonic()
    if _FACT_GEN_CACHE and now - _FACT_GEN_CACHE[0] < 30:
        return _FACT_GEN_CACHE[1]
    n = 0
    try:
        if strategic_ready():
            n = int(analytics_fact().estimated_document_count())
    except Exception:
        pass
    _FACT_GEN_CACHE = (now, n)
    return n


def _fact_has_data() -> bool:
    global _FACT_HAS_DATA_CACHE
    now = time.monotonic()
    if _FACT_HAS_DATA_CACHE and now - _FACT_HAS_DATA_CACHE[0] < 60:
        return _FACT_HAS_DATA_CACHE[1]
    has = False
    if strategic_ready():
        has = analytics_fact().find_one({}, {"_id": 1}) is not None
    _FACT_HAS_DATA_CACHE = (now, has)
    return has


def _cache_hit_usable(hit: Any) -> bool:
    if not _fact_has_data():
        return True
    if isinstance(hit, list) and len(hit) == 0:
        return False
    if isinstance(hit, dict) and hit.get("strategic_ready"):
        orders = int(hit.get("total_orders") or 0)
        if orders == 0:
            return False
        gen = _fact_gen()
        if gen > 0 and orders < gen * 0.95:
            return False
    return True


def _cache_get(key: str) -> Any | None:
    row = _CACHE.get(key)
    if not row:
        return None
    ts, val = row
    if time.monotonic() - ts > _CACHE_TTL_SEC:
        _CACHE.pop(key, None)
        return None
    if not _cache_hit_usable(val):
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, val: Any, *, skip_if_empty: bool = False) -> Any:
    if skip_if_empty:
        if isinstance(val, list) and len(val) == 0:
            return val
        if isinstance(val, dict) and val.get("strategic_ready") and not val.get("total_orders"):
            return val
    _CACHE[key] = (time.monotonic(), val)
    return val


def _cache_key(name: str, payload: dict[str, Any]) -> str:
    scoped = {**payload, "_fact_gen": _fact_gen()}
    raw = json.dumps(scoped, sort_keys=True, default=str)
    return name + ":" + hashlib.md5(raw.encode("utf-8")).hexdigest()


def clear_query_cache() -> None:
    global _MAX_DATE_CACHE, _FACT_HAS_DATA_CACHE, _FACT_GEN_CACHE, _FILTER_ANCHOR_CACHE
    _CACHE.clear()
    _DIM_NAME_CACHE.clear()
    _MAX_DATE_CACHE = None
    _FACT_HAS_DATA_CACHE = None
    _FACT_GEN_CACHE = None
    _FILTER_ANCHOR_CACHE = None


def _dim_name_to_id(collection: str, id_field: str, name_field: str = "name") -> dict[str, int]:
    """Mapa nombre→id en caché (evita find_one repetidos por request)."""
    now = time.monotonic()
    hit = _DIM_NAME_CACHE.get(collection)
    if hit and now - hit[0] < _DIM_CACHE_TTL_SEC:
        return hit[1]
    db = get_read_dw_db()
    mapping: dict[str, int] = {}
    for row in db[collection].find({}, {"_id": 0, id_field: 1, name_field: 1, "code": 1}):
        rid = row.get(id_field)
        if rid is None:
            continue
        label = str(row.get(name_field) or "").strip()
        if label:
            mapping[label] = int(rid)
        code = row.get("code")
        if code is not None:
            mapping[str(code).strip()] = int(rid)
    _DIM_NAME_CACHE[collection] = (now, mapping)
    return mapping


def _resolve_dim_id(collection: str, id_field: str, value: str | None, *, name_field: str = "name") -> int | None:
    if not value:
        return None
    mapping = _dim_name_to_id(collection, id_field, name_field=name_field)
    return mapping.get(str(value).strip())


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
    today = _utc_today_str()
    if val and val > today:
        val = today
    _MAX_DATE_CACHE = (now, val)
    return val


def dataset_filter_anchor_date() -> str | None:
    """Fecha máxima válida para anclar ventanas 12/24/48 meses.

    La versión anterior agrupaba toda ``fact_ventas`` por año antes de cada
    primera consulta. Con millones de filas ese escaneo retrasaba incluso los
    filtros más sencillos; la fecha máxima ya está cubierta por ``fact_fecha``.
    """
    global _FILTER_ANCHOR_CACHE
    now = time.monotonic()
    if _FILTER_ANCHOR_CACHE and now - _FILTER_ANCHOR_CACHE[0] < 300:
        return _FILTER_ANCHOR_CACHE[1]

    val = dataset_max_order_date()
    if isinstance(val, datetime):
        val = val.strftime("%Y-%m-%d")
    elif val is not None:
        val = str(val)[:10]
    _FILTER_ANCHOR_CACHE = (now, val)
    return val


def _dim_id_to_label(collection: str, id_field: str, *, name_field: str = "name") -> dict[int, str]:
    """Invierte el mapa de dimensiones que ya vive en caché."""
    return {int(rid): label for label, rid in _dim_name_to_id(collection, id_field, name_field).items()}


def dashboard_bundle(*, top: int = 10, **filters) -> dict[str, Any]:
    """Construye todo el tablero con un único recorrido sobre ``fact_ventas``."""
    key = _cache_key("dashboard_bundle", {**filters, "top": top, "layer": "fact"})
    hit = _cache_get(key)
    if hit is not None:
        return hit
    if not strategic_ready():
        return _cache_set(key, {
            "summary": _empty_summary(**filters), "trend": [], "regions": [],
            "channels": [], "priorities": [], "countries": [],
        })

    match = _fact_match(**filters)
    pipeline = _prefix(match) + [
        {"$project": {
            "fecha_id": 1, "region_id": 1, "country_id": 1,
            "category_id": 1, "channel_id": 1, "priority_id": 1,
            "total_revenue": 1, "total_profit": 1, "total_cost": 1,
        }},
        {"$facet": {
            "summary": [{"$group": {
                "_id": None, "revenue": {"$sum": "$total_revenue"},
                "profit": {"$sum": "$total_profit"}, "cost": {"$sum": "$total_cost"},
                "orders": {"$sum": 1}, "countries": {"$addToSet": "$country_id"},
                "categories": {"$addToSet": "$category_id"},
            }}],
            "trend": [
                {"$group": {"_id": {"$substr": ["$fecha_id", 0, 7]},
                    "revenue": {"$sum": "$total_revenue"}, "profit": {"$sum": "$total_profit"},
                    "orders": {"$sum": 1}}}, {"$sort": {"_id": 1}},
            ],
            "regions": [{"$group": {"_id": "$region_id", "revenue": {"$sum": "$total_revenue"},
                "profit": {"$sum": "$total_profit"}, "orders": {"$sum": 1}}}],
            "channels": [{"$group": {"_id": "$channel_id", "revenue": {"$sum": "$total_revenue"},
                "orders": {"$sum": 1}}}],
            "priorities": [{"$group": {"_id": "$priority_id", "orders": {"$sum": 1}}}],
            "countries": [{"$group": {"_id": "$country_id", "revenue": {"$sum": "$total_revenue"},
                "orders": {"$sum": 1}}}, {"$sort": {"revenue": -1}}, {"$limit": max(1, min(int(top), 50))}],
        }},
    ]
    raw_rows = list(analytics_fact().aggregate(pipeline, allowDiskUse=True))
    raw = raw_rows[0] if raw_rows else {}
    total = (raw.get("summary") or [{}])[0]
    revenue = float(total.get("revenue") or 0)
    months = filters.get("months")
    cutoff = _months_cutoff(months) if months and int(months) < 999 else None
    region_names = _dim_id_to_label("dim_region", "region_id")
    channel_names = _dim_id_to_label("dim_canal", "channel_id")
    priority_names = _dim_id_to_label("dim_prioridad", "priority_id", name_field="code")
    country_names = _dim_id_to_label("dim_pais", "country_id")
    lagging = False
    try:
        sync_meta = get_db()["app_meta"].find_one(
            {"_id": "strategic_sync"}, {"strategic_lagging": 1}
        ) or {}
        lagging = bool(sync_meta.get("strategic_lagging"))
    except Exception:
        pass

    summary = {
        "total_orders": int(total.get("orders") or 0), "total_revenue": round(revenue, 2),
        "total_profit": round(float(total.get("profit") or 0), 2),
        "total_cost": round(float(total.get("cost") or 0), 2),
        "avg_margin": round(float(total.get("profit") or 0) / revenue * 100, 2) if revenue else 0.0,
        "countries": len(total.get("countries") or []), "item_types": len(total.get("categories") or []),
        "dataset_max_date": dataset_max_order_date(), "filter_months": int(months) if cutoff else None,
        "filter_period_start": cutoff, "filter_anchor_date": dataset_filter_anchor_date() if cutoff else None,
        "historic_total_orders": int(_fact_gen()) if cutoff else int(total.get("orders") or 0),
        "strategic_ready": True, "strategic_lagging": lagging, "data_layer": "estrategico",
    }
    result = {
        "summary": summary,
        "trend": [{"month": r["_id"], "revenue": round(float(r.get("revenue") or 0), 2),
            "profit": round(float(r.get("profit") or 0), 2), "orders": int(r.get("orders") or 0)}
            for r in raw.get("trend", [])],
        "regions": sorted([{"region": region_names.get(int(r["_id"]), "Sin región"),
            "revenue": round(float(r.get("revenue") or 0), 2), "profit": round(float(r.get("profit") or 0), 2),
            "orders": int(r.get("orders") or 0)} for r in raw.get("regions", [])], key=lambda r: r["revenue"], reverse=True),
        "channels": [{"sales_channel": channel_names.get(int(r["_id"]), "Sin canal"),
            "revenue": round(float(r.get("revenue") or 0), 2), "orders": int(r.get("orders") or 0)}
            for r in raw.get("channels", [])],
        "priorities": sorted([{"order_priority": priority_names.get(int(r["_id"]), "M"),
            "orders": int(r.get("orders") or 0)} for r in raw.get("priorities", [])], key=lambda r: r["order_priority"]),
        "countries": [{"country": country_names.get(int(r["_id"]), "Sin país"),
            "revenue": round(float(r.get("revenue") or 0), 2), "orders": int(r.get("orders") or 0)}
            for r in raw.get("countries", [])],
    }
    return _cache_set(key, result, skip_if_empty=summary["total_orders"] == 0)


def _months_cutoff(months: int | None) -> str | None:
    if not months or months >= 999:
        return None
    anchor = dataset_filter_anchor_date() or _utc_today_str()
    try:
        end = datetime.strptime(anchor[:10], "%Y-%m-%d")
    except ValueError:
        end = _utc_now().replace(tzinfo=None)
    return (end - timedelta(days=int(months) * 31)).strftime("%Y-%m-%d")


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
        q["region_id"] = _resolve_dim_id("dim_region", "region_id", region) or -1
    if item_type:
        q["category_id"] = _resolve_dim_id("dim_categoria", "category_id", item_type) or -1
    if channel:
        q["channel_id"] = _resolve_dim_id("dim_canal", "channel_id", channel) or -1
    if priority:
        q["priority_id"] = _resolve_dim_id("dim_prioridad", "priority_id", priority) or -1
    if months and months < 999:
        cutoff = _months_cutoff(months)
        if cutoff:
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
        cutoff = _months_cutoff(months)
        if cutoff:
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
    orders = int(x.get("n") or 0)
    skip_cache = orders == 0 and strategic_ready()
    lagging = False
    try:
        doc = get_db()["app_meta"].find_one({"_id": "strategic_sync"}, {"strategic_lagging": 1}) or {}
        lagging = bool(doc.get("strategic_lagging"))
    except Exception:
        pass
    months = filters.get("months")
    cutoff = _months_cutoff(months) if months and int(months or 0) < 999 else None
    result = {
        "total_orders": orders,
        "total_revenue": round(rev, 2),
        "total_profit": round(float(x.get("p") or 0), 2),
        "total_cost": round(float(x.get("co") or 0), 2),
        "avg_margin": round(float((x.get("p") or 0) / rev * 100) if rev else 0, 2),
        "countries": countries,
        "item_types": item_types,
        "dataset_max_date": dataset_max_order_date(),
        "filter_months": int(months) if cutoff else None,
        "filter_period_start": cutoff,
        "filter_anchor_date": dataset_filter_anchor_date() if cutoff else None,
        "historic_total_orders": int(_fact_gen()) if cutoff else orders,
        "strategic_ready": True,
        "strategic_lagging": lagging,
        "data_layer": "estrategico",
    }
    return _cache_set(key, result, skip_if_empty=skip_cache)


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
                    "$group": {
                        "_id": "$region_id",
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                        "orders": {"$sum": 1},
                    }
                },
                {
                    "$lookup": {
                        "from": "dim_region",
                        "localField": "_id",
                        "foreignField": "region_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "region": {"$ifNull": ["$d.name", "Sin región"]},
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
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
                    "$group": {
                        "_id": "$category_id",
                        "units": {"$sum": "$units_sold"},
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                    }
                },
                {
                    "$lookup": {
                        "from": "dim_categoria",
                        "localField": "_id",
                        "foreignField": "category_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "item_type": {"$ifNull": ["$d.name", "Sin categoría"]},
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
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
                {"$limit": last_n if last_n < 999 else 600},
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
    rows = list(reversed(rows))
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
                    "$group": {
                        "_id": "$channel_id",
                        "orders": {"$sum": 1},
                        "revenue": {"$sum": "$total_revenue"},
                    }
                },
                {
                    "$lookup": {
                        "from": "dim_canal",
                        "localField": "_id",
                        "foreignField": "channel_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "sales_channel": {"$ifNull": ["$d.name", "Sin canal"]},
                        "orders": 1,
                        "revenue": {"$round": ["$revenue", 2]},
                        "_id": 0,
                    }
                },
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
                    "$group": {
                        "_id": "$priority_id",
                        "orders": {"$sum": 1},
                    }
                },
                {
                    "$lookup": {
                        "from": "dim_prioridad",
                        "localField": "_id",
                        "foreignField": "priority_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "order_priority": {"$ifNull": ["$d.code", "M"]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
                {"$sort": {"order_priority": 1}},
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
                    "$group": {
                        "_id": "$country_id",
                        "revenue": {"$sum": "$total_revenue"},
                        "orders": {"$sum": 1},
                    }
                },
                {"$sort": {"revenue": -1}},
                {"$limit": n},
                {
                    "$lookup": {
                        "from": "dim_pais",
                        "localField": "_id",
                        "foreignField": "country_id",
                        "as": "d",
                    }
                },
                {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
                {
                    "$project": {
                        "country": {"$ifNull": ["$d.name", "Sin país"]},
                        "revenue": {"$round": ["$revenue", 2]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
            ],
            allowDiskUse=True,
        )
    )
    return _cache_set(key, rows, skip_if_empty=not rows and strategic_ready())


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
