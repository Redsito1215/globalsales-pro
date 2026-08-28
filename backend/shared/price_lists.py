"""Listas de precios por cliente o canal con resolución determinista."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_price_list(data: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    list_id = int(data.get("price_list_id") or 0)
    scope = str(data.get("scope") or "channel").strip().lower()
    name = str(data.get("name") or "").strip()
    customer_email = str(data.get("customer_email") or "").strip().lower() or None
    channel_id = int(data.get("channel_id") or 0) or None
    if not name or scope not in {"customer", "channel"}:
        raise ValueError("invalid_price_list")
    if scope == "customer" and not customer_email:
        raise ValueError("price_list_customer_required")
    if scope == "channel" and not channel_id:
        raise ValueError("price_list_channel_required")
    if not list_id:
        last = db["price_lists"].find_one({}, {"price_list_id": 1}, sort=[("price_list_id", -1)])
        list_id = int((last or {}).get("price_list_id") or 0) + 1
    items = []
    adjustment_type = str(data.get("adjustment_type") or "fixed").strip().lower()
    adjustment_value = round(float(data.get("adjustment_value") or 0), 2)
    if adjustment_type not in {"fixed", "percentage"} or (adjustment_type == "percentage" and not -90 <= adjustment_value <= 500):
        raise ValueError("invalid_price_adjustment")
    for item in data.get("items") or []:
        pid, price = int(item.get("product_id") or 0), round(float(item.get("unit_price") or 0), 2)
        if pid < 1 or price <= 0:
            raise ValueError("invalid_price_list_item")
        items.append({"product_id": pid, "unit_price": price})
    if not items:
        raise ValueError("price_list_items_required")
    row = {"price_list_id": list_id, "name": name[:100], "scope": scope,
           "customer_email": customer_email if scope == "customer" else None,
           "channel_id": channel_id if scope == "channel" else None,
           "valid_from": str(data.get("valid_from") or "")[:10] or None,
           "valid_to": str(data.get("valid_to") or "")[:10] or None,
           "active": bool(data.get("active", True)), "items": items, "updated_at": _now()}
    row["adjustment_type"], row["adjustment_value"] = adjustment_type, adjustment_value
    db["price_lists"].update_one({"price_list_id": list_id}, {"$set": row, "$setOnInsert": {"created_at": _now()}}, upsert=True)
    log_audit("price_list_saved", entity="price_lists", entity_id=list_id, details={"name": name, "scope": scope, "items": len(items), "actor": actor_email})
    return db["price_lists"].find_one({"price_list_id": list_id}, {"_id": 0}) or row


def list_price_lists() -> list[dict[str, Any]]:
    return list(get_db()["price_lists"].find({}, {"_id": 0}).sort("price_list_id", 1))


def resolve_price(*, product_id: int, base_price: float, customer_email: str | None, channel_id: int | None) -> dict[str, Any]:
    today = date.today().isoformat()
    common = {"active": True, "$and": [{"$or": [{"valid_from": None}, {"valid_from": ""}, {"valid_from": {"$lte": today}}]},
                                      {"$or": [{"valid_to": None}, {"valid_to": ""}, {"valid_to": {"$gte": today}}]}]}
    db = get_db()
    candidates = []
    email = str(customer_email or "").strip().lower()
    if email:
        candidates.extend(db["price_lists"].find({**common, "scope": "customer", "customer_email": email}, {"_id": 0}))
    if channel_id:
        candidates.extend(db["price_lists"].find({**common, "scope": "channel", "channel_id": int(channel_id)}, {"_id": 0}))
    for row in candidates:  # cliente tiene prioridad porque se agregó primero
        for item in row.get("items") or []:
            if int(item.get("product_id") or 0) == int(product_id):
                price = float(item["unit_price"])
                if row.get("adjustment_type") == "percentage":
                    price = float(base_price or 0) * (1 + float(row.get("adjustment_value") or 0) / 100)
                return {"unit_price": round(max(price, 0), 2), "price_list_id": row.get("price_list_id"), "price_list_name": row.get("name")}
    return {"unit_price": round(float(base_price or 0), 2), "price_list_id": None, "price_list_name": None}
