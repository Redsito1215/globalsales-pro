"""Generar registros en sales_records — combinaciones aleatorias coherentes con la BD."""
from __future__ import annotations

import random
import string
from datetime import date, timedelta

from shared.mongo import sales_collection

DATE_START = date(2010, 1, 1)
DATE_END = date(2017, 12, 31)
BATCH_SIZE = 5_000
YEAR_MIN = 2010
YEAR_MAX = date.today().year


def _rand_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


def _next_order_id_start(col) -> int:
    """Máximo order_id NUMÉRICO (no lexicográfico) de sales_records + 1."""
    try:
        doc = next(
            col.aggregate(
                [
                    {
                        "$group": {
                            "_id": None,
                            "max": {
                                "$max": {
                                    "$convert": {"input": "$order_id", "to": "long", "onError": 0, "onNull": 0}
                                }
                            },
                        }
                    }
                ]
            )
        )
    except Exception:
        doc = None
    if doc and doc.get("max"):
        return int(doc["max"]) + 1
    return col.count_documents({}) + 1


def _load_catalogs_from_dims(db) -> dict | None:
    if db["dim_pais"].count_documents({}) == 0:
        return None
    country_region = []
    for pais in db["dim_pais"].find({}, {"_id": 0, "name": 1, "region_id": 1}):
        region = db["dim_region"].find_one({"region_id": pais.get("region_id")}, {"_id": 0, "name": 1})
        if pais.get("name") and region and region.get("name"):
            country_region.append({"country": pais["name"], "region": region["name"]})
    channels = [r["name"] for r in db["dim_canal"].find({}, {"_id": 0, "name": 1}) if r.get("name")]
    priorities = [
        r.get("code") or r.get("name", "")[:1]
        for r in db["dim_prioridad"].find({}, {"_id": 0, "code": 1, "name": 1})
        if r.get("code") or r.get("name")
    ]
    item_stats: dict[str, dict] = {}
    for cat in db["dim_categoria"].find({}, {"_id": 0, "name": 1}):
        cname = cat.get("name")
        if not cname:
            continue
        prods = list(db["dim_producto"].find({"category_id": cat.get("category_id")}, {"_id": 0}))
        if prods:
            ups = [float(p.get("unit_price") or 1) for p in prods]
            ucs = [float(p.get("unit_cost") or 1) for p in prods]
            item_stats[cname] = {
                "min_up": min(ups), "max_up": max(ups),
                "min_uc": min(ucs), "max_uc": max(ucs),
                "min_u": 1, "max_u": 500,
            }
        else:
            item_stats[cname] = {"min_up": 10, "max_up": 100, "min_uc": 5, "max_uc": 50, "min_u": 1, "max_u": 100}
    if not country_region or not channels or not item_stats:
        return None
    if not priorities:
        priorities = ["C", "H", "M", "L"]
    return {"country_region": country_region, "channels": channels, "priorities": priorities, "item_stats": item_stats}


def _load_catalogs(col) -> dict:
    from shared.mongo import get_db

    dims = _load_catalogs_from_dims(get_db())
    if dims:
        return dims

    n = col.count_documents({})
    if n == 0:
        raise ValueError(
            "No hay maestros ni sales_records. Carga maestros en Q4 o ejecuta ELT antes de generar."
        )

    country_region = []
    for row in col.aggregate(
        [
            {"$group": {"_id": {"country": "$country", "region": "$region"}}},
            {"$match": {"_id.country": {"$ne": None}, "_id.region": {"$ne": None}}},
        ]
    ):
        country_region.append(
            {"country": row["_id"]["country"], "region": row["_id"]["region"]}
        )
    if not country_region:
        raise ValueError("No hay pares país–región en sales_records.")

    channels = [c for c in col.distinct("sales_channel") if c]
    priorities = [p for p in col.distinct("order_priority") if p]
    if not channels or not priorities:
        raise ValueError("Faltan canales o prioridades en el catálogo.")

    item_stats: dict[str, dict] = {}
    for row in col.aggregate(
        [
            {
                "$group": {
                    "_id": "$item_type",
                    "min_up": {"$min": "$unit_price"},
                    "max_up": {"$max": "$unit_price"},
                    "min_uc": {"$min": "$unit_cost"},
                    "max_uc": {"$max": "$unit_cost"},
                    "min_u": {"$min": "$units_sold"},
                    "max_u": {"$max": "$units_sold"},
                }
            }
        ]
    ):
        it = row["_id"]
        if not it:
            continue
        item_stats[it] = {
            "min_up": float(row["min_up"] or 1),
            "max_up": float(row["max_up"] or 1),
            "min_uc": float(row["min_uc"] or 1),
            "max_uc": float(row["max_uc"] or 1),
            "min_u": int(row["min_u"] or 1),
            "max_u": int(row["max_u"] or 1000),
        }
    if not item_stats:
        raise ValueError("No hay tipos de producto en sales_records.")

    return {
        "country_region": country_region,
        "channels": channels,
        "priorities": priorities,
        "item_stats": item_stats,
    }


def _rand_date_pair(year: int | None = None) -> tuple[str, str]:
    if year is not None:
        start = date(int(year), 1, 1)
        end = date(int(year), 12, 31)
    else:
        start = DATE_START
        end = DATE_END
    span = (end - start).days
    if span < 1:
        span = 1
    order = start + timedelta(days=random.randint(0, span))
    ship = order + timedelta(days=random.randint(1, min(60, span or 1)))
    if ship > end:
        ship = end
    if ship < order:
        ship = order
    return order.isoformat(), ship.isoformat()


def _rand_in_range(lo: float, hi: float) -> float:
    if hi < lo:
        lo, hi = hi, lo
    return round(random.uniform(lo, hi), 2)


def _rand_int(lo: int, hi: int) -> int:
    if hi < lo:
        lo, hi = hi, lo
    return random.randint(lo, hi)


def _build_document(order_id: str, catalogs: dict, *, year: int | None = None) -> dict:
    geo = random.choice(catalogs["country_region"])
    item_type = random.choice(list(catalogs["item_stats"].keys()))
    st = catalogs["item_stats"][item_type]

    units = _rand_int(max(1, st["min_u"]), max(st["min_u"], st["max_u"]))
    unit_price = _rand_in_range(st["min_up"], st["max_up"])
    unit_cost = _rand_in_range(st["min_uc"], min(st["max_uc"], unit_price * 0.95))
    total_revenue = round(units * unit_price, 2)
    total_cost = round(units * unit_cost, 2)
    total_profit = round(total_revenue - total_cost, 2)
    order_date, ship_date = _rand_date_pair(year)

    return {
        "order_id": order_id,
        "region": geo["region"],
        "country": geo["country"],
        "item_type": item_type,
        "sales_channel": random.choice(catalogs["channels"]),
        "order_priority": random.choice(catalogs["priorities"]),
        "order_date": order_date,
        "ship_date": ship_date,
        "units_sold": units,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "id": _rand_id(),
    }


def generate_sales(count: int, *, year: int | None = None) -> dict:
    count = max(1, min(int(count), 500_000))
    if year is not None:
        year = int(year)
        if year < YEAR_MIN or year > YEAR_MAX:
            raise ValueError(f"El año debe estar entre {YEAR_MIN} y {YEAR_MAX}.")
    col = sales_collection()
    catalogs = _load_catalogs(col)
    order_start = _next_order_id_start(col)

    inserted = 0
    batch: list[dict] = []
    for i in range(count):
        oid = str(order_start + i)
        batch.append(_build_document(oid, catalogs, year=year))
        if len(batch) >= BATCH_SIZE:
            col.insert_many(batch, ordered=False)
            inserted += len(batch)
            batch = []

    if batch:
        col.insert_many(batch, ordered=False)
        inserted += len(batch)

    out = {"inserted": inserted, "total_after": col.count_documents({})}
    try:
        from shared.analytics_sync import sync_orders_bulk

        res = sync_orders_bulk(range(order_start, order_start + count))
        out["synced_to_fact"] = int(res.get("synced_orders") or 0)
        out["facts_inserted"] = int(res.get("facts_inserted") or 0)
        out["fact_ventas"] = col.database["fact_ventas"].count_documents({})
    except Exception as exc:
        out["sync_error"] = str(exc)
    if year is not None:
        out["year"] = year
    return out
