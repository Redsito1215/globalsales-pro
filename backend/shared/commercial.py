"""Políticas comerciales: vigencias, márgenes, excepciones y segmentación."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def margin_percent(*, revenue: float, cost: float) -> float:
    value = float(revenue or 0)
    return round((value - float(cost or 0)) / value * 100, 2) if value > 0 else 0.0


def discount_is_active(doc: dict[str, Any], *, at: datetime | None = None) -> bool:
    if not doc.get("active", True):
        return False
    instant = (at or datetime.now(timezone.utc)).date().isoformat()
    start = str(doc.get("valid_from") or "")[:10]
    end = str(doc.get("valid_to") or "")[:10]
    return (not start or start <= instant) and (not end or instant <= end)


def customer_segment(*, orders: int, spent: float) -> str:
    if orders >= 10 or spent >= 5000:
        return "vip"
    if orders >= 3 or spent >= 1000:
        return "frecuente"
    if orders == 0:
        return "nuevo"
    return "ocasional"


def record_product_terms(
    db: Any, *, product_id: int, before: dict[str, Any] | None,
    after: dict[str, Any], actor_email: str | None = None,
) -> dict[str, Any] | None:
    fields = ("unit_price", "unit_cost", "sale_enabled", "sale_percent")
    old = before or {}
    if all(old.get(key) == after.get(key) for key in fields):
        return None
    now = _now()
    db["product_price_history"].update_many(
        {"product_id": int(product_id), "effective_to": None}, {"$set": {"effective_to": now}}
    )
    doc = {
        "product_id": int(product_id),
        "unit_price": round(float(after.get("unit_price") or 0), 2),
        "unit_cost": round(float(after.get("unit_cost") or 0), 2),
        "sale_enabled": bool(after.get("sale_enabled")),
        "sale_percent": int(after.get("sale_percent") or 0),
        "margin_pct": margin_percent(revenue=after.get("unit_price") or 0, cost=after.get("unit_cost") or 0),
        "effective_from": now, "effective_to": None, "actor_email": actor_email,
    }
    db["product_price_history"].insert_one(doc)
    doc.pop("_id", None)
    return doc


def commercial_settings(db: Any | None = None) -> dict[str, Any]:
    database = db or get_db()
    current = database["shop_settings"].find_one({"shop_id": 1}, {"_id": 0}) or {}
    return {
        "minimum_order_amount": round(float(current.get("minimum_order_amount") or 0), 2),
        "maximum_order_amount": round(float(current.get("maximum_order_amount") or 0), 2),
        "minimum_margin_pct": round(float(current.get("minimum_margin_pct") or 0), 2),
        "default_customer_limit": round(float(current.get("default_customer_limit") or 0), 2),
    }


def update_commercial_settings(data: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    before = commercial_settings()
    values = {key: round(float(data.get(key) or 0), 2) for key in commercial_settings()}
    if any(value < 0 for value in values.values()) or values["minimum_margin_pct"] > 100:
        raise ValueError("invalid_commercial_settings")
    if values["maximum_order_amount"] and values["maximum_order_amount"] < values["minimum_order_amount"]:
        raise ValueError("invalid_commercial_settings")
    get_db()["shop_settings"].update_one({"shop_id": 1}, {"$set": values}, upsert=True)
    log_audit("commercial_settings", entity="shop_settings", entity_id=1, details=values, before=before, after=values)
    return values


def validate_checkout_policy(
    db: Any, *, email: str, subtotal: float, discount: float,
    lines: list[dict[str, Any]], exception_id: int | None = None,
) -> dict[str, Any]:
    settings = commercial_settings(db)
    net_revenue = round(float(subtotal or 0) - float(discount or 0), 2)
    total_cost = round(sum(float(x.get("unit_cost") or 0) * int(x.get("quantity") or 0) for x in lines), 2)
    margin = margin_percent(revenue=net_revenue, cost=total_cost)
    customer = db["customers"].find_one({"email": (email or "").strip().lower()}, {"_id": 0}) or {}
    customer_limit = float(customer.get("purchase_limit") or settings["default_customer_limit"] or 0)
    violations = []
    if net_revenue < settings["minimum_order_amount"]:
        violations.append("minimum_order")
    if settings["maximum_order_amount"] and net_revenue > settings["maximum_order_amount"]:
        violations.append("maximum_order")
    if customer_limit and net_revenue > customer_limit:
        violations.append("customer_limit")
    if margin < settings["minimum_margin_pct"]:
        violations.append("minimum_margin")
    exception = None
    if violations and exception_id:
        exception = db["commercial_exceptions"].find_one({
            "exception_id": int(exception_id), "status": "approved",
            "customer_email": (email or "").strip().lower(),
        }, {"_id": 0})
        if exception and float(exception.get("amount") or 0) and net_revenue > float(exception["amount"]):
            exception = None
        if exception and not set(violations).issubset(set(exception.get("violations") or [])):
            exception = None
    if violations and not exception:
        raise ValueError("commercial_exception_required:" + ",".join(violations))
    return {"net_revenue": net_revenue, "total_cost": total_cost, "margin_pct": margin, "violations": violations, "exception_id": exception_id if exception else None}


def segment_customer(db: Any, email: str) -> dict[str, Any]:
    clean = (email or "").strip().lower()
    rows = list(db["purchase_requests"].find({"client_email": clean, "status": {"$in": ["convertida", "enviada", "entregada"]}}, {"_id": 0, "total": 1, "created_at": 1}))
    orders = len(rows)
    spent = round(sum(float(x.get("total") or 0) for x in rows), 2)
    segment = customer_segment(orders=orders, spent=spent)
    return {"email": clean, "segment": segment, "orders_count": orders, "total_spent": spent}


def refresh_customer_segments(*, limit: int = 1000) -> list[dict[str, Any]]:
    db = get_db()
    emails = db["customers"].distinct("email")[:limit]
    rows = []
    for email in emails:
        row = segment_customer(db, email)
        db["customers"].update_one({"email": row["email"]}, {"$set": row})
        db["dim_cliente"].update_one({"email": row["email"]}, {"$set": {"segment": row["segment"]}})
        rows.append(row)
    log_audit("refresh_customer_segments", entity="customers", details={"count": len(rows)})
    return rows


def list_price_history(product_id: int, *, limit: int = 100) -> list[dict[str, Any]]:
    return list(get_db()["product_price_history"].find(
        {"product_id": int(product_id)}, {"_id": 0}
    ).sort("effective_from", -1).limit(min(limit, 500)))


def list_discounts(*, include_inactive: bool = True) -> list[dict[str, Any]]:
    query = {} if include_inactive else {"active": True}
    rows = list(get_db()["discount_codes"].find(query, {"_id": 0}).sort("discount_id", 1))
    for row in rows:
        row["currently_valid"] = discount_is_active(row)
    return rows


def save_discount(data: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    code = str(data.get("code") or "").strip().upper()
    value_type = str(data.get("value_type") or "percentage").strip().lower()
    value = round(float(data.get("value") or 0), 2)
    valid_from = str(data.get("valid_from") or "").strip()[:10] or None
    valid_to = str(data.get("valid_to") or "").strip()[:10] or None
    if not code or value <= 0 or value_type not in {"percentage", "fixed"}:
        raise ValueError("invalid_discount")
    if value_type == "percentage" and value > 100:
        raise ValueError("invalid_discount")
    if valid_from and valid_to and valid_to < valid_from:
        raise ValueError("invalid_discount_dates")
    existing = db["discount_codes"].find_one({"code": code}, {"_id": 0})
    row = {
        "code": code, "value_type": value_type, "value": value,
        "usage_limit": max(int(data.get("usage_limit") or 0), 0),
        "usage_count": int((existing or {}).get("usage_count") or 0),
        "minimum_order_amount": round(float(data.get("minimum_order_amount") or 0), 2),
        "allowed_segments": [str(x).lower() for x in (data.get("allowed_segments") or [])],
        "valid_from": valid_from, "valid_to": valid_to,
        "active": bool(data.get("active", True)), "updated_at": _now(),
    }
    if existing:
        row["discount_id"] = int(existing["discount_id"])
        db["discount_codes"].update_one({"code": code}, {"$set": row})
    else:
        last = db["discount_codes"].find_one({}, {"discount_id": 1}, sort=[("discount_id", -1)])
        row["discount_id"] = int((last or {}).get("discount_id") or 0) + 1
        row["created_at"] = _now()
        db["discount_codes"].insert_one(row)
    history = {**row, "changed_at": _now(), "actor_email": actor_email}
    history.pop("_id", None)
    db["discount_history"].insert_one(history)
    row.pop("_id", None)
    log_audit("discount_saved", entity="discount_codes", entity_id=code, details={"active": row["active"]})
    return {**row, "currently_valid": discount_is_active(row)}


def list_exceptions(*, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    query = {"status": status} if status else {}
    return list(get_db()["commercial_exceptions"].find(query, {"_id": 0}).sort("created_at", -1).limit(min(limit, 500)))


def mark_exception_used(db: Any, exception_id: int | None, *, request_id: int) -> None:
    if exception_id:
        db["commercial_exceptions"].update_one(
            {"exception_id": int(exception_id), "status": "approved"},
            {"$set": {"status": "used", "used_at": _now(), "request_id": int(request_id)}},
        )


def update_customer_terms(email: str, data: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    clean = (email or "").strip().lower()
    segment = str(data.get("segment") or "nuevo").strip().lower()
    if segment not in {"nuevo", "ocasional", "frecuente", "vip", "riesgo"}:
        raise ValueError("invalid_customer_segment")
    patch = {
        "segment": segment,
        "purchase_limit": round(float(data.get("purchase_limit") or 0), 2),
        "credit_limit": round(float(data.get("credit_limit") or 0), 2),
        "credit_days": max(min(int(data.get("credit_days") or 30), 365), 1),
        "credit_enabled": bool(data.get("credit_enabled")),
    }
    if patch["purchase_limit"] < 0 or patch["credit_limit"] < 0:
        raise ValueError("invalid_customer_terms")
    db = get_db()
    result = db["customers"].update_one({"email": clean}, {"$set": patch})
    if not result.matched_count:
        raise ValueError("customer_not_found")
    db["dim_cliente"].update_one({"email": clean}, {"$set": patch})
    log_audit("customer_commercial_terms", entity="customers", entity_id=clean, details=patch)
    return {"email": clean, **patch}


def create_exception(data: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    row = db["commercial_exceptions"].find_one({}, {"exception_id": 1}, sort=[("exception_id", -1)])
    exception_id = int((row or {}).get("exception_id") or 0) + 1
    reason = str(data.get("reason") or "").strip()
    customer_email = str(data.get("customer_email") or "").strip().lower()
    amount = round(float(data.get("amount") or 0), 2)
    violations = list(data.get("violations") or [])
    if len(reason) < 8:
        raise ValueError("reason_required")
    allowed_violations = {"minimum_order", "maximum_order", "customer_limit", "minimum_margin"}
    if not customer_email or amount <= 0 or not violations or not set(violations).issubset(allowed_violations):
        raise ValueError("invalid_exception")
    doc = {
        "exception_id": exception_id,
        "customer_email": customer_email, "amount": amount,
        "violations": violations, "reason": reason,
        "status": "pending", "requested_by": actor_email, "created_at": _now(),
    }
    db["commercial_exceptions"].insert_one(doc)
    doc.pop("_id", None)
    return doc


def decide_exception(exception_id: int, *, approved: bool, actor_email: str | None, reason: str) -> dict[str, Any]:
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 8:
        raise ValueError("reason_required")
    db = get_db()
    patch = {
        "status": "approved" if approved else "rejected", "decided_by": actor_email,
        "decision_reason": clean_reason, "decided_at": _now(),
    }
    result = db["commercial_exceptions"].update_one({"exception_id": int(exception_id), "status": "pending"}, {"$set": patch})
    if not result.matched_count:
        raise ValueError("exception_not_pending")
    row = db["commercial_exceptions"].find_one({"exception_id": int(exception_id)}, {"_id": 0})
    log_audit("commercial_exception_decision", entity="commercial_exceptions", entity_id=exception_id, details=patch)
    return row or {}


def set_product_featured(product_id: int, featured: bool, *, actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    result = db["dim_producto"].update_one({"product_id": int(product_id)}, {"$set": {"featured": bool(featured)}})
    if not result.matched_count:
        raise ValueError("not_found")
    db["products"].update_one({"product_id": int(product_id)}, {"$set": {"featured": bool(featured)}})
    log_audit("product_featured", entity="dim_producto", entity_id=product_id, details={"featured": bool(featured)})
    return {"product_id": int(product_id), "featured": bool(featured)}
