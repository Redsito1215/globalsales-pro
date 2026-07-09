"""Servicios Q3 — solicitudes de compra y ventas."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db, sales_collection
from shared.notifications import notify_user, status_message
from shared.roles_registry import ADMIN_ROLE

REQUEST_STATUSES = frozenset({"pendiente", "en_revision", "aprobada", "convertida", "rechazada", "cancelada"})


def _next_request_id(col) -> int:
    row = col.find_one({}, {"request_id": 1, "_id": 0}, sort=[("request_id", -1)])
    return int(row["request_id"]) + 1 if row and row.get("request_id") else 1


def _next_line_id(col) -> int:
    row = col.find_one({}, {"line_id": 1, "_id": 0}, sort=[("line_id", -1)])
    return int(row["line_id"]) + 1 if row and row.get("line_id") else 1


def list_requests(
    *,
    status: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    elif active_only:
        query["status"] = {"$nin": ["convertida", "rechazada", "cancelada"]}
    col = db["purchase_requests"]
    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).sort("request_id", -1).skip(offset).limit(limit))
    for row in rows:
        row["lines"] = list(
            db["purchase_request_lines"].find({"request_id": row["request_id"]}, {"_id": 0})
        )
    return {"total": total, "limit": limit, "offset": offset, "requests": rows}


def list_requests_for_email(email: str, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {
        "client_email": {"$regex": f"^{re.escape(email.strip())}$", "$options": "i"}
    }
    col = db["purchase_requests"]
    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).sort("request_id", -1).skip(offset).limit(limit))
    for row in rows:
        row["lines"] = list(
            db["purchase_request_lines"].find({"request_id": row["request_id"]}, {"_id": 0})
        )
    return {"total": total, "limit": limit, "offset": offset, "requests": rows}


def get_request(request_id: int) -> dict[str, Any] | None:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        return None
    req["lines"] = list(
        db["purchase_request_lines"].find({"request_id": int(request_id)}, {"_id": 0})
    )
    country = db["dim_pais"].find_one({"country_id": req.get("country_id")}, {"_id": 0, "name": 1})
    channel = db["dim_canal"].find_one({"channel_id": req.get("channel_id")}, {"_id": 0, "name": 1})
    if country:
        req["country_name"] = country.get("name")
    if channel:
        req["channel_name"] = channel.get("name")
    return req


def _notify_request_status(req: dict[str, Any], status: str) -> None:
    subject, body = status_message(status, int(req["request_id"]))
    notify_user(
        recipient_email=req.get("client_email") or "",
        subject=subject,
        body=body,
        category="pedido",
        request_id=int(req["request_id"]),
        meta={"status": status},
    )


def create_request(data: dict[str, Any]) -> dict[str, Any]:
    from shared.checkout_countries import ensure_checkout_countries

    ensure_checkout_countries()
    db = get_db()
    lines_in = data.get("lines") or []
    if not lines_in:
        raise ValueError("lines_required")
    client_name = (data.get("client_name") or "").strip()
    client_email = (data.get("client_email") or "").strip()
    if not client_name or not client_email:
        raise ValueError("client_required")

    country_id = int(data.get("country_id") or 0)
    channel_id = int(data.get("channel_id") or 1)
    country = db["dim_pais"].find_one({"country_id": country_id}, {"_id": 0})
    channel = db["dim_canal"].find_one({"channel_id": channel_id}, {"_id": 0})
    if not country:
        raise ValueError("invalid_country")
    if not channel:
        raise ValueError("invalid_channel")

    req_col = db["purchase_requests"]
    line_col = db["purchase_request_lines"]
    rid = _next_request_id(req_col)
    request_doc = {
        "request_id": rid,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": (data.get("client_phone") or "").strip() or None,
        "country_id": country_id,
        "channel_id": channel_id,
        "status": "pendiente",
        "notes": (data.get("notes") or "").strip() or None,
        "created_at": date.today().isoformat(),
        "reviewed_by": None,
        "order_id": None,
        "discount_code": (data.get("discount_code") or "").strip().upper() or None,
        "discount_amount": round(float(data.get("discount_amount") or 0), 2),
        "subtotal": round(float(data.get("subtotal") or 0), 2),
        "total": round(float(data.get("total") or 0), 2),
    }
    req_col.insert_one(request_doc)

    line_docs = []
    lid = _next_line_id(line_col)
    for item in lines_in:
        pid = int(item.get("product_id") or 0)
        qty = int(item.get("quantity") or 0)
        if pid < 1 or qty < 1:
            raise ValueError("invalid_line")
        prod = db["dim_producto"].find_one({"product_id": pid}, {"_id": 0})
        if not prod:
            raise ValueError("invalid_product")
        line_docs.append(
            {
                "line_id": lid,
                "request_id": rid,
                "product_id": pid,
                "product_name": prod.get("name"),
                "quantity": qty,
                "unit_price": float(prod.get("unit_price") or 0),
            }
        )
        lid += 1
    if line_docs:
        line_col.insert_many(line_docs)

    log_audit("create_request", entity="purchase_requests", entity_id=rid)
    full = get_request(rid) or request_doc
    _notify_request_status(full, "pendiente")
    return full


def cancel_request_by_client(request_id: int, *, client_email: str) -> dict[str, Any]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    if (req.get("client_email") or "").lower() != (client_email or "").lower():
        raise ValueError("forbidden")
    current = req.get("status")
    if current in ("convertida", "rechazada", "cancelada"):
        raise ValueError("cannot_cancel")
    if current == "aprobada":
        raise ValueError("cannot_cancel_approved")
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {"$set": {"status": "cancelada", "reviewed_by": client_email}},
    )
    log_audit("cancel_request", entity="purchase_requests", entity_id=request_id)
    full = get_request(request_id) or {}
    _notify_request_status(full, "cancelada")
    return full


def update_status(request_id: int, status: str, *, reviewer_email: str | None = None) -> dict[str, Any]:
    if status not in REQUEST_STATUSES:
        raise ValueError("invalid_status")
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    current = req.get("status")
    if current == "convertida":
        raise ValueError("already_converted")
    if current == "rechazada":
        raise ValueError("already_rejected")
    if current == "cancelada":
        raise ValueError("already_cancelled")
    if status == "rechazada" and current == "aprobada":
        raise ValueError("cannot_reject_approved")
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {"$set": {"status": status, "reviewed_by": reviewer_email}},
    )
    log_audit("update_request_status", entity="purchase_requests", entity_id=request_id, details={"status": status})
    full = get_request(request_id) or {}
    _notify_request_status(full, status)
    return full


def convert_to_sale(
    request_id: int,
    *,
    admin_email: str | None = None,
    actor_role: str | None = None,
) -> dict[str, Any]:
    db = get_db()
    req = get_request(request_id)
    if not req:
        raise ValueError("not_found")
    if req.get("status") == "convertida":
        raise ValueError("already_converted")
    if req.get("status") == "rechazada":
        raise ValueError("rejected")
    if req.get("status") == "cancelada":
        raise ValueError("cancelled")
    if actor_role != ADMIN_ROLE and req.get("status") != "aprobada":
        raise ValueError("approval_required")

    country = db["dim_pais"].find_one({"country_id": req["country_id"]}, {"_id": 0})
    region = db["dim_region"].find_one({"region_id": country["region_id"]}, {"_id": 0}) if country else None
    channel = db["dim_canal"].find_one({"channel_id": req["channel_id"]}, {"_id": 0})
    if not country or not region or not channel:
        raise ValueError("invalid_master_refs")

    col = sales_collection()
    last = col.find_one({}, {"order_id": 1, "_id": 0}, sort=[("order_id", -1)])
    try:
        next_oid = int(str(last["order_id"])) + 1 if last and last.get("order_id") else 1
    except ValueError:
        next_oid = col.count_documents({}) + 1

    order_date = date.today().isoformat()
    ship_date = (date.today() + timedelta(days=7)).isoformat()
    inserted = 0
    order_ids: list[str] = []

    for line in req.get("lines") or []:
        prod = db["dim_producto"].find_one({"product_id": line["product_id"]}, {"_id": 0})
        if not prod:
            continue
        cat = db["dim_categoria"].find_one({"category_id": prod["category_id"]}, {"_id": 0})
        item_type = cat["name"] if cat else prod.get("name", "Unknown")
        units = int(line["quantity"])
        unit_price = float(line.get("unit_price") or prod.get("unit_price") or 0)
        unit_cost = float(prod.get("unit_cost") or 0)
        oid = str(next_oid)
        next_oid += 1
        order_ids.append(oid)
        doc = {
            "order_id": oid,
            "region": region["name"],
            "country": country["name"],
            "item_type": item_type,
            "sales_channel": channel["name"],
            "order_priority": "M",
            "order_date": order_date,
            "ship_date": ship_date,
            "units_sold": units,
            "unit_price": unit_price,
            "unit_cost": unit_cost,
            "total_revenue": round(units * unit_price, 2),
            "total_cost": round(units * unit_cost, 2),
            "total_profit": round(units * (unit_price - unit_cost), 2),
        }
        col.insert_one(doc)
        inserted += 1

    if not inserted:
        raise ValueError("no_lines")

    primary_order_id = order_ids[0]
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {
            "$set": {
                "status": "convertida",
                "order_id": primary_order_id,
                "reviewed_by": admin_email,
            }
        },
    )
    log_audit(
        "convert_request",
        entity="purchase_requests",
        entity_id=request_id,
        details={"order_id": primary_order_id, "lines": inserted},
    )
    full = get_request(request_id) or {}
    _notify_request_status(full, "convertida")
    return {"request_id": request_id, "order_id": primary_order_id, "sales_inserted": inserted}


def list_store_products(*, category_id: int | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if category_id:
        query["category_id"] = int(category_id)
    col = db["dim_producto"]
    total = col.count_documents(query)
    rows = list(
        col.find(query, {"_id": 0, "product_id": 1, "name": 1, "category_id": 1, "unit_price": 1, "image_url": 1})
        .sort("product_id", 1)
        .skip(offset)
        .limit(limit)
    )
    return {"total": total, "products": rows}


def get_order(order_id: str) -> dict[str, Any] | None:
    rows = list(sales_collection().find({"order_id": str(order_id)}, {"_id": 0}))
    if not rows:
        return None
    return {"order_id": str(order_id), "lines": rows}


def create_order(data: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    region_name = (data.get("region") or "").strip()
    country_name = (data.get("country") or "").strip()
    item_type = (data.get("item_type") or "").strip()
    channel_name = (data.get("sales_channel") or data.get("channel") or "").strip()
    priority_code = (data.get("order_priority") or data.get("priority") or "M").strip()

    if not all([region_name, country_name, item_type, channel_name]):
        raise ValueError("fields_required")

    if not db["dim_region"].find_one({"name": region_name}):
        raise ValueError("invalid_region")
    if not db["dim_pais"].find_one({"name": country_name}):
        raise ValueError("invalid_country")
    if not db["dim_categoria"].find_one({"name": item_type}):
        raise ValueError("invalid_product")
    if not db["dim_canal"].find_one({"name": channel_name}):
        raise ValueError("invalid_channel")

    units = int(data.get("units_sold") or data.get("units") or 0)
    if units < 1:
        raise ValueError("invalid_units")

    unit_price = float(data.get("unit_price") or 0)
    unit_cost = float(data.get("unit_cost") or 0)
    if unit_price <= 0:
        prod = db["dim_producto"].find_one({"name": item_type}) or db["dim_categoria"].find_one({"name": item_type})
        if prod:
            unit_price = float(prod.get("unit_price") or 10)
            unit_cost = float(prod.get("unit_cost") or unit_price * 0.6)

    col = sales_collection()
    last = col.find_one({}, {"order_id": 1, "_id": 0}, sort=[("order_id", -1)])
    try:
        oid = str(int(str(last["order_id"])) + 1) if last and last.get("order_id") else "1"
    except ValueError:
        oid = str(col.count_documents({}) + 1)

    order_date = (data.get("order_date") or date.today().isoformat())[:10]
    ship = data.get("ship_date")
    ship_date = ship[:10] if ship else (date.today() + timedelta(days=7)).isoformat()

    doc = {
        "order_id": oid,
        "region": region_name,
        "country": country_name,
        "item_type": item_type,
        "sales_channel": channel_name,
        "order_priority": priority_code[:1].upper(),
        "order_date": order_date,
        "ship_date": ship_date,
        "units_sold": units,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
        "total_revenue": round(units * unit_price, 2),
        "total_cost": round(units * unit_cost, 2),
        "total_profit": round(units * (unit_price - unit_cost), 2),
    }
    col.insert_one(doc)
    log_audit("create_order", entity="sales_records", entity_id=oid, details=doc)
    return doc


def update_order(order_id: str, data: dict[str, Any]) -> dict[str, Any]:
    col = sales_collection()
    existing = col.find_one({"order_id": str(order_id)})
    if not existing:
        raise ValueError("not_found")
    patch: dict[str, Any] = {}
    for key in (
        "region", "country", "item_type", "sales_channel", "order_priority",
        "order_date", "ship_date", "units_sold", "unit_price", "unit_cost",
    ):
        if key in data and data[key] is not None and data[key] != "":
            patch[key] = data[key]
    if "channel" in data and data["channel"]:
        patch["sales_channel"] = data["channel"]
    if "priority" in data and data["priority"]:
        patch["order_priority"] = str(data["priority"])[:1].upper()
    if "units" in data:
        patch["units_sold"] = int(data["units"])

    base = {**existing, **patch}
    units = int(base.get("units_sold") or 0)
    up = float(base.get("unit_price") or 0)
    uc = float(base.get("unit_cost") or 0)
    patch["total_revenue"] = round(units * up, 2)
    patch["total_cost"] = round(units * uc, 2)
    patch["total_profit"] = round(units * (up - uc), 2)

    col.update_many({"order_id": str(order_id)}, {"$set": patch})
    log_audit("update_order", entity="sales_records", entity_id=order_id, details=patch)
    row = col.find_one({"order_id": str(order_id)}, {"_id": 0})
    return dict(row) if row else {}


def delete_order(order_id: str) -> int:
    col = sales_collection()
    n = col.count_documents({"order_id": str(order_id)})
    if not n:
        raise ValueError("not_found")
    col.delete_many({"order_id": str(order_id)})
    log_audit("delete_order", entity="sales_records", entity_id=order_id, details={"deleted": n})
    return n
