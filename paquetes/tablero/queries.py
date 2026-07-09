"""Consultas MongoDB — Cuadrante Q1 (tablero)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from shared.mongo import sales_collection


def _match(
    region: str | None = None,
    item_type: str | None = None,
    channel: str | None = None,
    priority: str | None = None,
    months: int | None = None,
) -> dict[str, Any]:
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
        cutoff = (datetime.utcnow() - timedelta(days=months * 31)).strftime("%Y-%m-%d")
        q["order_date"] = {"$gte": cutoff}
    return q


def _prefix(match: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"$match": match}] if match else []


def get_summary(**filters) -> dict[str, Any]:
    match = _match(**filters)
    pipe = _prefix(match) + [
        {
            "$group": {
                "_id": None,
                "r": {"$sum": "$total_revenue"},
                "p": {"$sum": "$total_profit"},
                "co": {"$sum": "$total_cost"},
                "n": {"$sum": 1},
            }
        }
    ]
    c = sales_collection()
    rows = list(c.aggregate(pipe))
    x = rows[0] if rows else {}
    rev = float(x.get("r") or 0)
    total = x.get("n") or c.count_documents(match)
    countries = len(c.distinct("country", match)) if match else len(c.distinct("country"))
    item_types = len(c.distinct("item_type", match)) if match else len(c.distinct("item_type"))
    return {
        "total_orders": int(total),
        "total_revenue": round(rev, 2),
        "total_profit": round(float(x.get("p") or 0), 2),
        "total_cost": round(float(x.get("co") or 0), 2),
        "avg_margin": round(float((x.get("p") or 0) / rev * 100) if rev else 0, 2),
        "countries": countries,
        "item_types": item_types,
    }


def revenue_by_region(**filters):
    match = _match(**filters)
    return list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": "$region",
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
            ]
        )
    )


def revenue_by_product(**filters):
    match = _match(**filters)
    return list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": "$item_type",
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
            ]
        )
    )


def monthly_trend(last_n: int = 24, **filters):
    match = _match(**filters)
    rows = list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": {"$substr": ["$order_date", 0, 7]},
                        "revenue": {"$sum": "$total_revenue"},
                        "profit": {"$sum": "$total_profit"},
                        "orders": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": -1}},
                {"$limit": last_n},
                {
                    "$project": {
                        "month": "$_id",
                        "revenue": {"$round": ["$revenue", 2]},
                        "profit": {"$round": ["$profit", 2]},
                        "orders": 1,
                        "_id": 0,
                    }
                },
            ]
        )
    )
    return list(reversed(rows))


def channel_breakdown(**filters):
    match = _match(**filters)
    return list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": "$sales_channel",
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
            ]
        )
    )


def priority_breakdown(**filters):
    match = _match(**filters)
    return list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {"$group": {"_id": "$order_priority", "orders": {"$sum": 1}}},
                {"$project": {"order_priority": "$_id", "orders": 1, "_id": 0}},
                {"$sort": {"order_priority": 1}},
            ]
        )
    )


def top_countries(n: int = 10, **filters):
    match = _match(**filters)
    return list(
        sales_collection().aggregate(
            _prefix(match)
            + [
                {
                    "$group": {
                        "_id": "$country",
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
            ]
        )
    )


def search_orders(
    country=None,
    item_type=None,
    channel=None,
    priority=None,
    region=None,
    limit=50,
    offset=0,
):
    q = _match(region=region, item_type=item_type, channel=channel, priority=priority)
    if country:
        q["country"] = {"$regex": country, "$options": "i"}
    return list(
        sales_collection()
        .find(q, {"_id": 0})
        .sort("order_date", -1)
        .skip(offset)
        .limit(limit)
    )


def count_orders(**kwargs):
    q = _match(
        region=kwargs.get("region"),
        item_type=kwargs.get("item_type"),
        channel=kwargs.get("channel"),
        priority=kwargs.get("priority"),
    )
    if kwargs.get("country"):
        q["country"] = {"$regex": kwargs["country"], "$options": "i"}
    return sales_collection().count_documents(q)


def ping_mongo() -> bool:
    try:
        sales_collection().database.client.admin.command("ping")
        return True
    except Exception:
        return False
