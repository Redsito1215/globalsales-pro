"""Servicios Q3 — solicitudes de compra y ventas."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from auth import roles_service
from paquetes.tablero import catalogo_nombres as nom
from shared.audit import log_audit
from shared.mongo import get_db, sales_collection
from shared.notifications import notify_roles, notify_user, status_message
from shared.roles_registry import ADMIN_ROLE

REQUEST_STATUSES = frozenset(
    {
        "pendiente",
        "en_revision",
        "aprobada",
        "convertida",
        "enviada",
        "entregada",
        "devolucion_parcial",
        "devuelta",
        "rechazada",
        "cancelada",
    }
)
ACTIVE_STATUSES = frozenset({"pendiente", "en_revision", "aprobada", "convertida", "enviada", "devolucion_parcial"})
RESTOCK_STATUSES = frozenset({"rechazada", "cancelada"})
POST_SALE_STATUSES = frozenset({"enviada", "entregada"})
PAYMENT_ALLOWED_STATUSES = frozenset({"aprobada"})
PAYMENT_STATUSES = frozenset({"pendiente_pago", "parcial", "pagado", "credito"})
PAYMENT_METHODS = frozenset({"tarjeta"})
RETURN_CONDITIONS = frozenset({"apto", "danado", "mixto"})
EC_TZ = ZoneInfo("America/Guayaquil")


def _now_ec_iso() -> str:
    return datetime.now(EC_TZ).replace(microsecond=0).isoformat()


def _parse_non_negative_number(value: Any, field: str, *, allow_zero: bool = True) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if number < 0 or (not allow_zero and number <= 0):
        raise ValueError(f"invalid_{field}")
    return number


def _clean_phone(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits or raw.lstrip().startswith("-"):
        raise ValueError("invalid_phone")
    return raw


def _record_request_event(
    db, request_id: int, event_type: str, *, actor_email: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    db["request_events"].insert_one({
        "request_id": int(request_id), "event_type": event_type,
        "actor_email": actor_email, "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def request_timeline(request_id: int) -> list[dict[str, Any]]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    rows = list(db["request_events"].find({"request_id": int(request_id)}, {"_id": 0}).sort("created_at", 1))
    created_at = req.get("created_at")
    if created_at and not any(x.get("event_type") == "created" for x in rows):
        rows.insert(0, {"request_id": int(request_id), "event_type": "created", "created_at": created_at, "details": {"status": "pendiente"}})
    return rows


def payment_receipt(request_id: int) -> dict[str, Any]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    attempt = db["payment_attempts"].find_one(
        {"request_id": int(request_id), "outcome": "approved"}, {"_id": 0}, sort=[("attempt_id", -1)]
    )
    if not attempt or req.get("payment_status") != "pagado":
        raise ValueError("payment_required")
    from shared.accounting import get_or_create_invoice
    invoice = get_or_create_invoice(req)
    return {
        "request_id": int(request_id), "order_id": req.get("order_id"),
        "client_name": req.get("client_name"), "amount": attempt.get("amount"),
        "currency": attempt.get("currency", "USD"), "paid_at": attempt.get("created_at"),
        "transaction_reference": attempt.get("transaction_reference"),
        "payment_method": "tarjeta", "card": attempt.get("card"),
        "invoice_number": invoice.get("invoice_number"),
    }


def _allocate_discount(gross_amounts: list[float], discount: float) -> list[float]:
    """Prorratea descuento por línea; el residuo cae en la última con monto > 0."""
    n = len(gross_amounts)
    if n == 0:
        return []
    discount = max(0.0, float(discount or 0))
    total = sum(gross_amounts)
    if discount <= 0 or total <= 0:
        return [0.0] * n
    shares = [round(discount * (g / total), 2) for g in gross_amounts]
    diff = round(discount - sum(shares), 2)
    if diff:
        for i in range(n - 1, -1, -1):
            if gross_amounts[i] > 0:
                shares[i] = round(shares[i] + diff, 2)
                break
    return shares


def _next_request_id(col) -> int:
    row = col.find_one({}, {"request_id": 1, "_id": 0}, sort=[("request_id", -1)])
    return int(row["request_id"]) + 1 if row and row.get("request_id") else 1


def _next_line_id(col) -> int:
    row = col.find_one({}, {"line_id": 1, "_id": 0}, sort=[("line_id", -1)])
    return int(row["line_id"]) + 1 if row and row.get("line_id") else 1


def _localized_product_name(*, product_id: int | None, fallback: str = "") -> str:
    if product_id is not None:
        name = nom.product_display_name_by_id(int(product_id), "")
        if name:
            return name
    return (fallback or "").strip() or (f"Producto {product_id}" if product_id else "Producto")


def _localize_request_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in lines:
        row = dict(line)
        pid = row.get("product_id")
        row["product_name"] = _localized_product_name(
            product_id=int(pid) if pid is not None else None,
            fallback=str(row.get("product_name") or ""),
        )
        out.append(row)
    return out


def _maybe_restock(req: dict[str, Any]) -> None:
    if req.get("stock_restored"):
        return
    lines = req.get("stock_lines") or []
    if not lines:
        return
    from paquetes.shop.services import restock_lines

    restock_lines(lines)
    get_db()["purchase_requests"].update_one(
        {"request_id": int(req["request_id"])},
        {"$set": {"stock_restored": True}},
    )
    log_audit(
        "restock_request",
        entity="purchase_requests",
        entity_id=int(req["request_id"]),
        details={"lines": len(lines)},
    )


def list_requests(
    *,
    status: str | None = None,
    active_only: bool = False,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    elif active_only:
        query["status"] = {"$in": list(ACTIVE_STATUSES)}
    term = (q or "").strip()
    if term:
        rx = {"$regex": re.escape(term), "$options": "i"}
        query["$or"] = [
            {"client_name": rx},
            {"client_email": rx},
            {"notes": rx},
        ]
        if term.isdigit():
            query["$or"].append({"request_id": int(term)})
    col = db["purchase_requests"]
    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).sort("request_id", -1).skip(offset).limit(limit))
    for row in rows:
        row["lines"] = list(
            db["purchase_request_lines"].find({"request_id": row["request_id"]}, {"_id": 0})
        )
        _normalize_request_row(row)
    return {"total": total, "limit": limit, "offset": offset, "requests": rows}


def count_pending_requests() -> int:
    return get_db()["purchase_requests"].count_documents(
        {"status": {"$in": ["pendiente", "en_revision", "aprobada"]}}
    )


def _client_order_numbers(col, query: dict[str, Any]) -> dict[int, int]:
    """Número de pedido 1..N por cliente (orden cronológico), independiente del request_id global."""
    ids = [
        int(r["request_id"])
        for r in col.find(query, {"request_id": 1, "_id": 0}).sort("request_id", 1)
        if r.get("request_id") is not None
    ]
    return {rid: i + 1 for i, rid in enumerate(ids)}


def list_requests_for_email(email: str, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {
        "client_email": {"$regex": f"^{re.escape(email.strip())}$", "$options": "i"}
    }
    col = db["purchase_requests"]
    total = col.count_documents(query)
    order_nos = _client_order_numbers(col, query)
    rows = list(col.find(query, {"_id": 0}).sort("request_id", -1).skip(offset).limit(limit))
    for row in rows:
        rid = int(row["request_id"])
        row["client_order_no"] = order_nos.get(rid, 0)
        row["lines"] = list(
            db["purchase_request_lines"].find({"request_id": rid}, {"_id": 0})
        )
        _normalize_request_row(row)
    return {"total": total, "limit": limit, "offset": offset, "requests": rows}


def _client_email_registered(email: str) -> bool:
    addr = (email or "").strip()
    if not addr:
        return False
    return bool(
        get_db()["users"].find_one(
            {"email": {"$regex": f"^{re.escape(addr)}$", "$options": "i"}},
            {"_id": 1},
        )
    )


def _payment_methods_for(req: dict[str, Any]) -> frozenset[str]:
    del req  # Un solo medio: tarjeta, en todos los canales.
    return PAYMENT_METHODS


def _normalize_payment_method(method: str, req: dict[str, Any]) -> str:
    m = (method or "").strip().lower()
    allowed = _payment_methods_for(req)
    if m not in allowed:
        raise ValueError("invalid_payment_method")
    return m


def _request_expected_total(req: dict[str, Any]) -> float:
    if req.get("total") is not None:
        return round(float(req["total"]), 2)
    subtotal = float(req.get("subtotal") or 0)
    discount = float(req.get("discount_amount") or 0)
    shipping = float(req.get("shipping_cost") or 0)
    return round(max(subtotal - discount + shipping, 0.0), 2)


def _payment_settled(req: dict[str, Any]) -> bool:
    """Pago completo: estado pagado (o crédito offline) y monto abonado = total."""
    pay = req.get("payment_status") or "pendiente_pago"
    if pay == "credito":
        return _is_offline_channel(req)
    if pay != "pagado":
        return False
    expected = _request_expected_total(req)
    paid_raw = req.get("paid_amount")
    paid = round(float(paid_raw if paid_raw is not None else expected), 2)
    return abs(paid - expected) < 0.01


def _is_offline_channel(channel_or_req: dict[str, Any] | None) -> bool:
    """Ventas presenciales (canal Offline) no pasan por envío."""
    if not channel_or_req:
        return False
    name = (channel_or_req.get("channel_name") or channel_or_req.get("name") or "").strip().lower()
    if name == "offline":
        return True
    cid = channel_or_req.get("channel_id")
    try:
        return int(cid) == 2
    except (TypeError, ValueError):
        return False


def _payment_allows_progress(req: dict[str, Any]) -> bool:
    return _payment_settled(req)


def _require_approved_for_payment(req: dict[str, Any]) -> None:
    if req.get("status") not in PAYMENT_ALLOWED_STATUSES:
        raise ValueError("approval_required_for_payment")


def validate_credit_exposure(customer: dict[str, Any], *, current_exposure: float, requested: float) -> float:
    if not customer.get("credit_enabled"):
        raise ValueError("credit_not_enabled")
    limit = round(float(customer.get("credit_limit") or 0), 2)
    exposure = round(float(current_exposure or 0) + float(requested or 0), 2)
    if not limit or exposure > limit + 0.009:
        raise ValueError("credit_limit_exceeded")
    return exposure


def platform_order_id(request_id: int) -> str:
    """ID único de venta generada desde una solicitud de la plataforma."""
    return f"V-{int(request_id):05d}"


def display_order_id(order_id: Any, request_id: Any = None) -> str:
    """Etiqueta legible; corrige el ID erróneo 1000000000 del histórico CSV."""
    oid = str(order_id or "").strip()
    if not oid:
        return ""
    if oid == "1000000000" and request_id is not None:
        try:
            return platform_order_id(int(request_id))
        except (TypeError, ValueError):
            pass
    return oid


def repair_legacy_platform_order_ids(db=None) -> int:
    """Reasigna pedidos de plataforma que quedaron con order_id=1000000000."""
    db = db or get_db()
    fixed = 0
    for req in db["purchase_requests"].find({"order_id": "1000000000"}, {"request_id": 1}):
        rid = int(req["request_id"])
        new_id = platform_order_id(rid)
        db["purchase_requests"].update_one({"request_id": rid}, {"$set": {"order_id": new_id}})
        db["sales_records"].update_many({"request_id": rid}, {"$set": {"order_id": new_id}})
        fixed += 1
    return fixed


def _normalize_request_row(row: dict[str, Any]) -> None:
    if row.get("lines"):
        row["lines"] = _localize_request_lines(row["lines"])
    if row.get("order_id"):
        row["order_id"] = display_order_id(row["order_id"], row.get("request_id"))
    email = (row.get("client_email") or "").strip()
    row["client_user_registered"] = _client_email_registered(email) if email else False


def get_request(request_id: int) -> dict[str, Any] | None:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        return None
    req["lines"] = _localize_request_lines(
        list(db["purchase_request_lines"].find({"request_id": int(request_id)}, {"_id": 0}))
    )
    country = db["dim_pais"].find_one({"country_id": req.get("country_id")}, {"_id": 0, "name": 1})
    channel = db["dim_canal"].find_one({"channel_id": req.get("channel_id")}, {"_id": 0, "name": 1})
    if country:
        req["country_name"] = country.get("name")
    if channel:
        req["channel_name"] = channel.get("name")
    email = (req.get("client_email") or "").strip()
    if email:
        q = {"client_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
        req["client_order_no"] = _client_order_numbers(db["purchase_requests"], q).get(int(request_id), 0)
    if req.get("order_id"):
        req["order_id"] = display_order_id(req["order_id"], req.get("request_id"))
    email = (req.get("client_email") or "").strip()
    req["client_user_registered"] = _client_email_registered(email) if email else False
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


def _notify_staff_new_request(req: dict[str, Any]) -> None:
    rid = int(req["request_id"])
    client = req.get("client_name") or req.get("client_email") or "Cliente"
    notify_roles(
        roles=("vendedor", "administrador"),
        subject=f"Nueva solicitud #{rid}",
        body=(
            f"{client} envió la solicitud #{rid}.\n"
            f"Revisa Checkouts / Ventas para gestionarla."
        ),
        category="comercial",
        request_id=rid,
        meta={"status": "pendiente"},
        exclude_email=req.get("client_email"),
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
    active_master = {"$ne": False}
    country = db["dim_pais"].find_one({"country_id": country_id, "active": active_master}, {"_id": 0})
    channel = db["dim_canal"].find_one({"channel_id": channel_id, "active": active_master}, {"_id": 0})
    if not country:
        raise ValueError("invalid_country")
    if not channel:
        raise ValueError("invalid_channel")

    stock_lines = []
    for item in data.get("stock_lines") or []:
        try:
            stock_lines.append(
                {
                    "variant_id": int(item.get("variant_id") or 0),
                    "quantity": int(item.get("quantity") or 0),
                }
            )
        except (TypeError, ValueError):
            continue
    stock_lines = [x for x in stock_lines if x["variant_id"] > 0 and x["quantity"] > 0]

    req_col = db["purchase_requests"]
    line_col = db["purchase_request_lines"]
    rid = _next_request_id(req_col)
    request_doc = {
        "request_id": rid,
        "client_name": client_name,
        "client_email": client_email,
        "client_phone": _clean_phone(data.get("client_phone")),
        "country_id": country_id,
        "channel_id": channel_id,
        "status": "pendiente",
        "payment_status": "pendiente_pago",
        "paid_at": None,
        "paid_amount": None,
        "payment_due": round(_parse_non_negative_number(data.get("total"), "total"), 2) if data.get("total") else None,
        "notes": (data.get("notes") or "").strip() or None,
        "created_at": _now_ec_iso(),
        "reviewed_by": None,
        "order_id": None,
        "discount_code": (data.get("discount_code") or "").strip().upper() or None,
        "discount_amount": round(_parse_non_negative_number(data.get("discount_amount"), "discount_amount"), 2),
        "subtotal": round(_parse_non_negative_number(data.get("subtotal"), "subtotal"), 2),
        "shipping_cost": round(_parse_non_negative_number(data.get("shipping_cost"), "shipping_cost"), 2),
        "shipping_destination": (data.get("shipping_destination") or data.get("destination") or "").strip() or None,
        "shipping_region": (data.get("shipping_region") or "").strip() or None,
        "total": round(_parse_non_negative_number(data.get("total"), "total"), 2),
        "commercial_policy": data.get("commercial_policy") or None,
        "stock_lines": stock_lines,
        "stock_restored": False,
        "stock_committed_closed": False,
        "tracking_number": None,
        "shipped_at": None,
        "delivered_at": None,
    }
    req_col.insert_one(request_doc)

    line_docs = []
    lid = _next_line_id(line_col)
    built_gross: list[float] = []
    for item in lines_in:
        pid = int(item.get("product_id") or 0)
        qty = int(item.get("quantity") or 0)
        if pid < 1 or qty < 1:
            raise ValueError("invalid_line")
        prod = db["dim_producto"].find_one({"product_id": pid, "active": {"$ne": False}}, {"_id": 0})
        if not prod:
            raise ValueError("invalid_product")
        # Prioridad: precio de variante/checkout > maestro
        if item.get("unit_price") is not None and item.get("unit_price") != "":
            unit_price = _parse_non_negative_number(item["unit_price"], "unit_price", allow_zero=False)
        else:
            unit_price = _parse_non_negative_number(prod.get("unit_price"), "unit_price", allow_zero=False)
        if item.get("unit_cost") is not None and item.get("unit_cost") != "":
            unit_cost = _parse_non_negative_number(item["unit_cost"], "unit_cost")
        else:
            unit_cost = _parse_non_negative_number(prod.get("unit_cost"), "unit_cost")
        line_gross = round(unit_price * qty, 2)
        built_gross.append(line_gross)
        line_docs.append(
            {
                "line_id": lid,
                "request_id": rid,
                "product_id": pid,
                "product_name": _localized_product_name(
                    product_id=pid,
                    fallback=str(prod.get("name") or ""),
                ),
                "quantity": qty,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "variant_id": int(item["variant_id"]) if item.get("variant_id") else None,
                "line_gross": line_gross,
                "discount_alloc": 0.0,
                "line_net": line_gross,
            }
        )
        lid += 1

    discount_amount = round(_parse_non_negative_number(data.get("discount_amount"), "discount_amount"), 2)
    shares = _allocate_discount(built_gross, discount_amount)
    for i, doc in enumerate(line_docs):
        share = shares[i] if i < len(shares) else 0.0
        doc["discount_alloc"] = share
        doc["line_net"] = round(max(doc["line_gross"] - share, 0.0), 2)

    calc_subtotal = round(sum(built_gross), 2)
    shipping_cost = round(_parse_non_negative_number(data.get("shipping_cost"), "shipping_cost"), 2)
    calc_total = round(max(calc_subtotal - discount_amount + shipping_cost, 0.0), 2)
    if not data.get("subtotal"):
        request_doc["subtotal"] = calc_subtotal
        req_col.update_one({"request_id": rid}, {"$set": {"subtotal": calc_subtotal}})
    if data.get("shipping_cost") is None and shipping_cost:
        request_doc["shipping_cost"] = shipping_cost
        req_col.update_one({"request_id": rid}, {"$set": {"shipping_cost": shipping_cost}})
    if not data.get("total"):
        request_doc["total"] = calc_total
        req_col.update_one({"request_id": rid}, {"$set": {"total": calc_total}})
    if request_doc.get("payment_due") is None:
        request_doc["payment_due"] = calc_total
        req_col.update_one({"request_id": rid}, {"$set": {"payment_due": calc_total}})

    if line_docs:
        line_col.insert_many(line_docs)

    _record_request_event(db, rid, "created", actor_email=client_email, details={"status": "pendiente", "total": request_doc.get("total")})
    log_audit("create_request", entity="purchase_requests", entity_id=rid)
    full = get_request(rid) or request_doc
    _notify_request_status(full, "pendiente")
    _notify_staff_new_request(full)
    return full


def cancel_request_by_client(request_id: int, *, client_email: str) -> dict[str, Any]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    if (req.get("client_email") or "").lower() != (client_email or "").lower():
        raise ValueError("forbidden")
    current = req.get("status")
    if current in ("convertida", "enviada", "entregada", "rechazada", "cancelada"):
        raise ValueError("cannot_cancel")
    if current == "aprobada":
        raise ValueError("cannot_cancel_approved")
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {"$set": {"status": "cancelada", "reviewed_by": client_email}},
    )
    _maybe_restock(req)
    _record_request_event(db, request_id, "status_changed", actor_email=client_email, details={"from": current, "to": "cancelada"})
    log_audit("cancel_request", entity="purchase_requests", entity_id=request_id)
    full = get_request(request_id) or {}
    _notify_request_status(full, "cancelada")
    return full


# Transiciones permitidas vía PATCH /estado (sin atajos a convertida/devuelta/cancelada)
_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "pendiente": frozenset({"en_revision", "aprobada", "rechazada"}),
    "en_revision": frozenset({"pendiente", "aprobada", "rechazada"}),
    "aprobada": frozenset(),  # postventa solo vía /convertir, /estado enviada|entregada
    "convertida": frozenset({"enviada"}),
    "enviada": frozenset({"entregada"}),
}


def update_status(request_id: int, status: str, *, reviewer_email: str | None = None) -> dict[str, Any]:
    if status not in REQUEST_STATUSES:
        raise ValueError("invalid_status")
    # Estas salidas tienen endpoints dedicados (convierten venta, restock, etc.)
    if status in ("convertida", "devuelta", "cancelada"):
        raise ValueError("use_dedicated_endpoint")

    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    current = req.get("status")

    if current == "entregada":
        raise ValueError("already_delivered")
    if current == "devuelta":
        raise ValueError("already_returned")
    if current == "rechazada":
        raise ValueError("already_rejected")
    if current == "cancelada":
        raise ValueError("already_cancelled")
    if status == "rechazada" and current == "aprobada":
        raise ValueError("cannot_reject_approved")

    offline = _is_offline_channel(req)
    if status == "enviada" and offline:
        raise ValueError("offline_no_shipping")

    allowed = _STATUS_TRANSITIONS.get(str(current) if current else "", frozenset())
    if offline and current == "convertida" and status == "entregada":
        allowed = frozenset({"entregada"})
    if status not in allowed:
        if status == "enviada":
            if offline:
                raise ValueError("offline_no_shipping")
            raise ValueError("must_convert_first")
        if status == "entregada":
            raise ValueError("must_ship_first")
        raise ValueError("invalid_transition")

    # Postventa: convertida → enviada → entregada (Offline: convertida → entregada)
    if status in ("enviada", "entregada") and not _payment_allows_progress(req):
        raise ValueError("payment_required")

    patch: dict[str, Any] = {"status": status, "reviewed_by": reviewer_email}
    if status == "enviada":
        patch["shipped_at"] = date.today().isoformat()
        patch["carrier"] = req.get("carrier") or "Transporte interno"
        patch["estimated_delivery"] = req.get("estimated_delivery") or (date.today() + timedelta(days=7)).isoformat()
        if not req.get("tracking_number"):
            patch["tracking_number"] = f"GT-{int(request_id):06d}"
    if status == "entregada":
        patch["delivered_at"] = date.today().isoformat()
        if not req.get("shipped_at"):
            patch["shipped_at"] = date.today().isoformat()
        if not offline and not req.get("tracking_number"):
            patch["tracking_number"] = f"GT-{int(request_id):06d}"

    db["purchase_requests"].update_one({"request_id": int(request_id)}, {"$set": patch})
    if status in RESTOCK_STATUSES:
        _maybe_restock(req)
    log_audit(
        "update_request_status",
        entity="purchase_requests",
        entity_id=request_id,
        details={"status": status},
    )
    _record_request_event(db, request_id, "status_changed", actor_email=reviewer_email, details={"from": req.get("status"), "to": status})
    full = get_request(request_id) or {}
    _notify_request_status(full, status)
    return full


def update_payment(
    request_id: int,
    payment_status: str,
    *,
    reviewer_email: str | None = None,
    payment_method: str | None = None,
    payment_attempt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError("invalid_payment")
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    if req.get("status") in ("rechazada", "cancelada"):
        raise ValueError("cannot_pay_closed")
    if payment_status in ("pagado", "credito"):
        _require_approved_for_payment(req)
    if payment_status == "pagado":
        from shared.accounting import assert_period_open
        assert_period_open()
    if payment_status == "credito":
        ch = db["dim_canal"].find_one({"channel_id": req.get("channel_id")}, {"_id": 0, "name": 1})
        if not _is_offline_channel(ch or {"channel_id": req.get("channel_id")}):
            raise ValueError("credit_offline_only")
        email = str(req.get("client_email") or "").strip().lower()
        customer = db["customers"].find_one({"email": email}, {"_id": 0}) or {}
        open_rows = db["purchase_requests"].find({
            "client_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"},
            "payment_status": "credito", "request_id": {"$ne": int(request_id)},
            "status": {"$nin": ["rechazada", "cancelada", "devuelta"]},
        }, {"subtotal": 1, "discount_amount": 1, "shipping_cost": 1, "total": 1})
        validate_credit_exposure(
            customer,
            current_exposure=sum(_request_expected_total(row) for row in open_rows),
            requested=_request_expected_total(req),
        )
    patch: dict[str, Any] = {
        "payment_status": payment_status,
        "reviewed_by": reviewer_email,
    }
    if payment_status == "pagado":
        expected = _request_expected_total(req)
        patch["paid_at"] = date.today().isoformat()
        patch["paid_amount"] = expected
        patch["payment_due"] = expected
        if payment_method:
            patch["payment_method"] = str(payment_method)[:40]
    elif payment_status == "credito":
        credit_days = max(min(int(customer.get("credit_days") or 30), 365), 1)
        patch["paid_at"] = None
        patch["paid_amount"] = 0.0
        patch["payment_due"] = _request_expected_total(req)
        patch["credit_days"] = credit_days
        patch["credit_due_date"] = (date.today() + timedelta(days=credit_days)).isoformat()
    elif payment_status == "pendiente_pago":
        patch["paid_at"] = None
        patch["paid_amount"] = None
    db["purchase_requests"].update_one({"request_id": int(request_id)}, {"$set": patch})
    # Sincronizar en sales_records si ya se convirtió
    oid = req.get("order_id")
    if oid:
        sales_collection().update_many(
            {"order_id": str(oid)},
            {"$set": {"payment_status": payment_status}},
        )
    log_audit(
        "update_payment",
        entity="purchase_requests",
        entity_id=request_id,
        details={"payment_status": payment_status, "paid_amount": patch.get("paid_amount")},
    )
    _record_request_event(
        db, request_id, "payment_updated", actor_email=reviewer_email,
        details={
            "payment_status": payment_status, "amount": patch.get("paid_amount"),
            "transaction_reference": (payment_attempt or {}).get("transaction_reference"),
            "card": (payment_attempt or {}).get("card"),
        },
    )
    full = get_request(request_id) or {}
    if payment_status == "pagado":
        from shared.cash_ledger import record_cash_movement

        record_cash_movement(
            movement_type="payment_in",
            amount=float(patch.get("paid_amount") or _request_expected_total(full)),
            request_id=int(request_id),
            order_id=full.get("order_id"),
            payment_method=patch.get("payment_method"),
            actor_email=reviewer_email,
            reference=(payment_attempt or {}).get("transaction_reference") or f"Pago solicitud #{request_id}",
        )
    notify_user(
        recipient_email=full.get("client_email") or "",
        subject=f"Solicitud #{request_id} — pago {payment_status.replace('_', ' ')}",
        body=(
            f"El estado de pago de tu solicitud #{request_id} es: {payment_status.replace('_', ' ')}.\n"
            f"Revisa Mis pedidos en Altavia Trade."
        ),
        category="pago",
        request_id=int(request_id),
        meta={"payment_status": payment_status},
    )
    return full


def client_pay(
    request_id: int,
    *,
    client_email: str,
    method: str = "tarjeta",
    card: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """El cliente confirma el pago de su propia solicitud."""
    email = (client_email or "").strip().lower()
    if not email:
        raise ValueError("forbidden")
    req = get_request(int(request_id))
    if not req:
        raise ValueError("not_found")
    if (req.get("client_email") or "").strip().lower() != email:
        raise ValueError("forbidden")
    if req.get("status") in ("rechazada", "cancelada", "devuelta"):
        raise ValueError("cannot_pay_closed")
    db = get_db()
    existing = db["payment_attempts"].find_one({"idempotency_key": str(idempotency_key or "").strip()}, {"_id": 0})
    if existing and int(existing.get("request_id") or 0) == int(request_id) and existing.get("outcome") == "approved":
        return req
    if (req.get("payment_status") or "pendiente_pago") == "pagado":
        raise ValueError("already_paid")
    _require_approved_for_payment(req)
    method_norm = _normalize_payment_method(method, req)
    from shared.payments import record_payment_attempt
    attempt, _ = record_payment_attempt(
        db, request_id=request_id, amount=_request_expected_total(req), outcome="approved",
        idempotency_key=idempotency_key, card=card or {}, actor_email=email,
    )
    return update_payment(
        request_id,
        "pagado",
        reviewer_email=email,
        payment_method=method_norm,
        payment_attempt=attempt,
    )


def staff_register_payment(
    request_id: int,
    *,
    staff_email: str,
    method: str,
    card: dict[str, Any] | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Vendedor/admin registra pago cuando el cliente no puede (offline o correo sin cuenta)."""
    req = get_request(int(request_id))
    if not req:
        raise ValueError("not_found")
    if req.get("status") in ("rechazada", "cancelada", "devuelta"):
        raise ValueError("cannot_pay_closed")
    if (req.get("payment_status") or "pendiente_pago") == "pagado":
        raise ValueError("already_paid")
    _require_approved_for_payment(req)
    offline = _is_offline_channel(req)
    registered = bool(req.get("client_user_registered"))
    if not offline and registered:
        raise ValueError("client_must_pay")
    method_norm = _normalize_payment_method(method, req)
    reviewer = (staff_email or "").strip()
    from shared.payments import record_payment_attempt
    attempt, _ = record_payment_attempt(
        get_db(), request_id=request_id, amount=_request_expected_total(req), outcome="approved",
        idempotency_key=idempotency_key, card=card or {}, actor_email=reviewer,
    )
    return update_payment(
        request_id,
        "pagado",
        reviewer_email=reviewer,
        payment_method=method_norm,
        payment_attempt=attempt,
    )


def record_failed_payment_attempt(
    request_id: int, *, actor_email: str, outcome: str, idempotency_key: str,
    card: dict[str, Any], failure_code: str | None = None, allow_staff: bool = False,
) -> dict[str, Any]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    email = (actor_email or "").strip().lower()
    if not allow_staff and (req.get("client_email") or "").strip().lower() != email:
        raise ValueError("forbidden")
    if outcome == "approved":
        raise ValueError("invalid_payment_outcome")
    from shared.payments import record_payment_attempt
    attempt, _ = record_payment_attempt(
        db, request_id=request_id, amount=_request_expected_total(req), outcome=outcome,
        idempotency_key=idempotency_key, card=card, actor_email=email, failure_code=failure_code,
    )
    _record_request_event(
        db, request_id, "payment_failed", actor_email=email,
        details={"outcome": attempt.get("outcome"), "card": attempt.get("card")},
    )
    return attempt


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
    if req.get("status") in ("convertida", "enviada", "entregada"):
        raise ValueError("already_converted")
    if req.get("status") == "rechazada":
        raise ValueError("rejected")
    if req.get("status") == "cancelada":
        raise ValueError("cancelled")
    can_bypass = actor_role == ADMIN_ROLE or roles_service.has_permission(
        actor_role, "ventas.convert_bypass"
    )
    if not can_bypass and req.get("status") != "aprobada":
        raise ValueError("approval_required")

    if not _payment_settled(req):
        pay = req.get("payment_status") or "pendiente_pago"
        if pay == "pagado":
            raise ValueError("payment_amount_mismatch")
        raise ValueError("payment_required_before_convert")

    country = db["dim_pais"].find_one({"country_id": req["country_id"]}, {"_id": 0})
    region = db["dim_region"].find_one({"region_id": country["region_id"]}, {"_id": 0}) if country else None
    channel = db["dim_canal"].find_one({"channel_id": req["channel_id"]}, {"_id": 0})
    if not country or not region or not channel:
        raise ValueError("invalid_master_refs")

    lines = list(req.get("lines") or [])
    if not lines:
        raise ValueError("no_lines")

    # Recalcular prorrateo si líneas viejas no tienen discount_alloc
    grosses = []
    for line in lines:
        qty = int(line.get("quantity") or 0)
        up = float(line.get("unit_price") or 0)
        grosses.append(round(qty * up, 2))
    discount = float(req.get("discount_amount") or 0)
    shares = _allocate_discount(grosses, discount)
    for i, line in enumerate(lines):
        if line.get("discount_alloc") is None:
            line["discount_alloc"] = shares[i]
        if line.get("line_net") is None:
            line["line_net"] = round(max(grosses[i] - float(line.get("discount_alloc") or 0), 0), 2)

    col = sales_collection()
    order_id = platform_order_id(int(request_id))
    order_date = date.today().isoformat()
    ship_date = (date.today() + timedelta(days=7)).isoformat()
    payment_status = req.get("payment_status") or "pendiente_pago"
    inserted = 0

    for line in lines:
        prod = db["dim_producto"].find_one({"product_id": line["product_id"]}, {"_id": 0})
        if not prod:
            continue
        cat = db["dim_categoria"].find_one({"category_id": prod["category_id"]}, {"_id": 0})
        item_type = cat["name"] if cat else prod.get("name", "Unknown")
        units = int(line["quantity"])
        list_price = float(line.get("unit_price") or prod.get("unit_price") or 0)
        unit_cost = float(line.get("unit_cost") if line.get("unit_cost") is not None else (prod.get("unit_cost") or 0))
        disc = float(line.get("discount_alloc") or 0)
        revenue = float(line.get("line_net")) if line.get("line_net") is not None else round(units * list_price - disc, 2)
        revenue = max(revenue, 0.0)
        # Precio efectivo neto para coherencia de KPIs (revenue ≈ units * unit_price)
        net_unit = round(revenue / units, 4) if units else 0.0
        cost_total = round(units * unit_cost, 2)
        doc = {
            "order_id": order_id,
            "request_id": int(request_id),
            "region": region["name"],
            "country": country["name"],
            "item_type": item_type,
            "sales_channel": channel["name"],
            "order_priority": "M",
            "order_date": order_date,
            "ship_date": ship_date,
            "units_sold": units,
            "unit_price": net_unit,
            "list_unit_price": list_price,
            "discount_alloc": disc,
            "discount_code": req.get("discount_code"),
            "unit_cost": unit_cost,
            "total_revenue": round(revenue, 2),
            "total_cost": cost_total,
            "total_profit": round(revenue - cost_total, 2),
            "payment_status": payment_status,
            "product_id": line.get("product_id"),
            "product_name": line.get("product_name"),
        }
        col.insert_one(doc)
        inserted += 1

    if not inserted:
        raise ValueError("no_lines")

    # Cerrar committed de inventario
    if not req.get("stock_committed_closed"):
        from paquetes.shop.services import finalize_committed

        finalize_committed(req.get("stock_lines") or [])

    offline = _is_offline_channel(channel)
    status_patch: dict[str, Any] = {
        "order_id": order_id,
        "reviewed_by": admin_email,
        "stock_committed_closed": True,
    }
    if offline:
        today = date.today().isoformat()
        status_patch.update(
            {
                "status": "entregada",
                "delivered_at": today,
                "shipped_at": today,
                "tracking_number": None,
            }
        )
    else:
        status_patch["status"] = "convertida"

    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {"$set": status_patch},
    )
    log_audit(
        "convert_request",
        entity="purchase_requests",
        entity_id=request_id,
        details={
            "order_id": order_id,
            "lines": inserted,
            "discount": discount,
            "offline": offline,
        },
    )
    full = get_request(request_id) or {}
    _notify_request_status(full, "entregada" if offline else "convertida")

    analytics_stale = True
    sync_info: dict[str, Any] = {}
    try:
        from shared.analytics_sync import set_strategic_lag, sync_order_to_fact

        sync_info = sync_order_to_fact(order_id)
        analytics_stale = bool(sync_info.get("analytics_stale", False))
    except Exception as exc:
        sync_info = {"error": str(exc)}
        try:
            from shared.analytics_sync import set_strategic_lag

            set_strategic_lag(True, detail=f"convert {order_id}: {exc}")
        except Exception:
            pass

    return {
        "request_id": request_id,
        "order_id": order_id,
        "sales_inserted": inserted,
        "discount_amount": discount,
        "payment_status": payment_status,
        "offline_sale": offline,
        "final_status": "entregada" if offline else "convertida",
        "analytics_stale": analytics_stale,
        "analytics_sync": sync_info,
        "data_layer": "landing" if analytics_stale else "estrategico",
        "message_analytics": (
            (
                "Venta en landing (sales_records). Sync a fact_ventas falló; "
                "usa Datos → Sincronizar / Construir modelo."
            )
            if analytics_stale
            else "Venta en landing y sincronizada a fact_ventas (Tablero al día)."
        ),
    }


def _request_stock_lines(req: dict[str, Any]) -> list[dict[str, Any]]:
    """Líneas de stock asociadas a la solicitud (variant_id + quantity)."""
    lines = list(req.get("stock_lines") or [])
    if lines:
        out = []
        for line in lines:
            vid = int(line.get("variant_id") or 0)
            qty = int(line.get("quantity") or 0)
            if vid >= 1 and qty >= 1:
                out.append({"variant_id": vid, "quantity": qty, "product_id": int(line.get("product_id") or 0)})
        return out
    db = get_db()
    out = []
    for line in db["purchase_request_lines"].find({"request_id": int(req["request_id"])}):
        qty = int(line.get("quantity") or 0)
        vid = int(line.get("variant_id") or 0)
        pid = int(line.get("product_id") or 0)
        if qty < 1:
            continue
        if vid < 1 and pid:
            variant = db["product_variants"].find_one({"product_id": pid}, {"variant_id": 1})
            vid = int((variant or {}).get("variant_id") or 0)
        if vid < 1:
            continue
        out.append({"variant_id": vid, "quantity": qty, "product_id": pid})
    return out


def plan_return_stock(
    stock_lines: list[dict[str, Any]],
    *,
    condition: str,
    inspections: list[dict[str, Any]] | None = None,
    partial: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Decide qué unidades reingresan a stock (apto) y cuáles no (dañado).
    condition: apto | danado | mixto
    inspections (solo mixto): [{variant_id, restock_qty, damaged_qty}]
    """
    condition = (condition or "").strip().lower()
    if condition not in RETURN_CONDITIONS:
        raise ValueError("return_condition_required")
    if not stock_lines:
        raise ValueError("no_lines")

    by_vid = {int(l["variant_id"]): int(l["quantity"]) for l in stock_lines}

    if condition == "apto":
        restock = [{"variant_id": vid, "quantity": qty} for vid, qty in by_vid.items()]
        return restock, []

    if condition == "danado":
        damaged = [{"variant_id": vid, "quantity": qty} for vid, qty in by_vid.items()]
        return [], damaged

    # mixto: inspección por línea obligatoria
    if not inspections:
        raise ValueError("return_inspection_required")
    restock_map: dict[int, int] = {}
    damaged_map: dict[int, int] = {}
    seen: set[int] = set()
    for item in inspections:
        vid = int(item.get("variant_id") or 0)
        if vid < 1 or vid not in by_vid:
            raise ValueError("invalid_return_line")
        if vid in seen:
            raise ValueError("duplicate_return_line")
        seen.add(vid)
        ok = int(item.get("restock_qty") if item.get("restock_qty") is not None else item.get("quantity_ok") or 0)
        bad = int(item.get("damaged_qty") if item.get("damaged_qty") is not None else item.get("quantity_damaged") or 0)
        if ok < 0 or bad < 0:
            raise ValueError("invalid_return_qty")
        ordered = by_vid[vid]
        if (not partial and ok + bad != ordered) or (partial and (ok + bad < 1 or ok + bad > ordered)):
            raise ValueError("return_qty_mismatch")
        if ok:
            restock_map[vid] = ok
        if bad:
            damaged_map[vid] = bad
    missing = set(by_vid) - seen
    if missing and not partial:
        raise ValueError("return_inspection_incomplete")
    restock = [{"variant_id": vid, "quantity": qty} for vid, qty in restock_map.items()]
    damaged = [{"variant_id": vid, "quantity": qty} for vid, qty in damaged_map.items()]
    return restock, damaged


def _apply_restock_qty(db, variant_id: int, qty: int) -> None:
    if qty < 1 or variant_id < 1:
        return
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        return
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)}) or {}
    before = int(variant.get("inventory_quantity") or 0)
    db["product_variants"].update_one(
        {"variant_id": int(variant_id)},
        {"$inc": {"inventory_quantity": int(qty)}},
    )
    inv = db["inventory_items"].find_one({"variant_id": int(variant_id)})
    if inv:
        db["inventory_levels"].update_one(
            {"inventory_item_id": inv["inventory_item_id"]},
            {"$inc": {"available": int(qty)}},
        )
    try:
        from shared.inventory_ledger import record_movement
        record_movement(
            db, variant_id=int(variant_id), movement_type="customer_return", quantity=int(qty),
            before=before, after=before + int(qty), reason="Reingreso apto por devolución de cliente",
        )
    except Exception:
        pass


def _returned_units_by_product(
    stock_lines: list[dict[str, Any]],
    restock_lines: list[dict[str, Any]],
    damaged_lines: list[dict[str, Any]],
) -> dict[int, int]:
    vid_to_pid: dict[int, int] = {}
    for line in stock_lines:
        vid_to_pid[int(line["variant_id"])] = int(line.get("product_id") or 0)
    by_pid: dict[int, int] = {}
    for line in restock_lines + damaged_lines:
        vid = int(line["variant_id"])
        pid = vid_to_pid.get(vid) or 0
        if pid > 0:
            by_pid[pid] = by_pid.get(pid, 0) + int(line["quantity"])
    return by_pid


def _reverse_sale_revenue_for_return(
    *,
    order_id: str,
    returned_by_product: dict[int, int],
    reason: str | None = None,
    condition: str | None = None,
) -> float:
    """Reduce revenue/cost/profit in landing proporcional a unidades devueltas."""
    col = sales_collection()
    rows = list(col.find({"order_id": str(order_id)}))
    if not rows:
        return 0.0
    total_reversal = 0.0
    today = date.today().isoformat()
    for row in rows:
        pid = int(row.get("product_id") or 0)
        returned_units = int(returned_by_product.get(pid) or 0)
        if returned_units <= 0:
            continue
        units = int(row.get("units_sold") or 0)
        if units <= 0:
            continue
        ratio = min(returned_units / units, 1.0)
        rev = float(row.get("total_revenue") or 0)
        cost = float(row.get("total_cost") or 0)
        profit = float(row.get("total_profit") if row.get("total_profit") is not None else rev - cost)
        rev_delta = round(rev * ratio, 2)
        cost_delta = round(cost * ratio, 2)
        profit_delta = round(profit * ratio, 2)
        total_reversal += rev_delta
        new_units = max(units - returned_units, 0)
        new_rev = round(max(rev - rev_delta, 0), 2)
        new_cost = round(max(cost - cost_delta, 0), 2)
        new_profit = round(max(profit - profit_delta, 0), 2)
        net_unit = round(new_rev / new_units, 4) if new_units else 0.0
        col.update_one(
            {"_id": row["_id"]},
            {
                "$set": {
                    "returned": True,
                    "returned_at": today,
                    "return_reason": (reason or "").strip() or None,
                    "return_condition": (condition or "").strip().lower() or None,
                    "units_sold": new_units,
                    "total_revenue": new_rev,
                    "total_cost": new_cost,
                    "total_profit": new_profit,
                    "unit_price": net_unit,
                    "revenue_reversed": round(float(row.get("revenue_reversed") or 0) + rev_delta, 2),
                }
            },
        )
    return round(total_reversal, 2)


def return_delivered_request(
    request_id: int,
    *,
    reviewer_email: str | None = None,
    reason: str | None = None,
    condition: str | None = None,
    inspections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Devolución post-entrega: solo reingresa a stock lo inspeccionado como apto."""
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    if req.get("status") not in {"entregada", "devolucion_parcial"}:
        raise ValueError("must_be_delivered")
    if req.get("status") == "devuelta":
        raise ValueError("already_returned")
    if req.get("payment_status") == "pagado":
        from shared.accounting import assert_period_open

        assert_period_open()

    stock_lines = _request_stock_lines(req)
    previous_events = list(req.get("return_events") or [])
    returned_before: dict[int, int] = {}
    for event in previous_events:
        for line in (event.get("restock_lines") or []) + (event.get("damaged_lines") or []):
            vid = int(line.get("variant_id") or 0)
            returned_before[vid] = returned_before.get(vid, 0) + int(line.get("quantity") or 0)
    stock_lines = [
        {**line, "quantity": int(line["quantity"]) - returned_before.get(int(line["variant_id"]), 0)}
        for line in stock_lines
        if int(line["quantity"]) - returned_before.get(int(line["variant_id"]), 0) > 0
    ]
    restock_lines, damaged_lines = plan_return_stock(
        stock_lines,
        condition=condition or "",
        inspections=inspections,
        partial=bool(inspections),
    )

    for line in restock_lines:
        _apply_restock_qty(db, int(line["variant_id"]), int(line["quantity"]))
    if restock_lines and req.get("lot_allocations"):
        from shared.inventory_lots import restore_allocated_lots
        restore_allocated_lots(allocations=req.get("lot_allocations") or [], returned_lines=restock_lines,
                               request_id=int(request_id), actor_email=reviewer_email)

    # Registro de merma / no reingreso (no vuelve a available)
    if damaged_lines:
        scrap_docs = []
        for line in damaged_lines:
            scrap_docs.append(
                {
                    "request_id": int(request_id),
                    "variant_id": int(line["variant_id"]),
                    "quantity": int(line["quantity"]),
                    "reason": (reason or "").strip() or None,
                    "created_at": date.today().isoformat(),
                    "reviewed_by": reviewer_email,
                }
            )
        if scrap_docs:
            db["inventory_scrapped"].insert_many(scrap_docs)

    oid = req.get("order_id")
    refund_total = 0.0
    if oid:
        returned_by_product = _returned_units_by_product(stock_lines, restock_lines, damaged_lines)
        refund_total = _reverse_sale_revenue_for_return(
            order_id=str(oid),
            returned_by_product=returned_by_product,
            reason=reason,
            condition=condition,
        )
        if refund_total > 0:
            try:
                from shared.analytics_sync import sync_order_to_fact

                sync_order_to_fact(str(oid), force=True)
            except Exception:
                pass
            try:
                from shared.accounting import create_credit_note

                create_credit_note(
                    amount=refund_total,
                    request_id=int(request_id),
                    actor_email=reviewer_email,
                    reason=(reason or f"Devolución de solicitud #{request_id}").strip(),
                    source="return",
                )
            except Exception:
                raise

    restock_units = sum(int(l["quantity"]) for l in restock_lines)
    damaged_units = sum(int(l["quantity"]) for l in damaged_lines)
    event_units = restock_units + damaged_units
    if event_units < 1:
        raise ValueError("invalid_return_qty")
    total_ordered = sum(int(l.get("quantity") or 0) for l in _request_stock_lines(req))
    total_returned = sum(returned_before.values()) + event_units
    is_complete = total_returned >= total_ordered
    cumulative_refund = round(float(req.get("return_refund_amount") or 0) + refund_total, 2)
    return_event = {
        "event_id": len(previous_events) + 1, "returned_at": datetime.now(timezone.utc).isoformat(),
        "reason": (reason or "").strip() or None, "condition": (condition or "").strip().lower(),
        "restock_lines": restock_lines, "damaged_lines": damaged_lines,
        "units": event_units, "refund_amount": round(refund_total, 2), "reviewed_by": reviewer_email,
    }
    paid_amount = float(req.get("paid_amount") or 0)
    refund_status = "sin_reembolso"
    if cumulative_refund > 0:
        refund_status = "reembolsado" if cumulative_refund >= paid_amount else "reembolso_parcial"
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {
            "$set": {
                "status": "devuelta" if is_complete else "devolucion_parcial",
                "returned_at": date.today().isoformat() if is_complete else None,
                "last_return_at": return_event["returned_at"],
                "return_reason": (reason or "").strip() or None,
                "return_condition": (condition or "").strip().lower(),
                "return_restock_lines": restock_lines,
                "return_damaged_lines": damaged_lines,
                "return_restock_units": int(req.get("return_restock_units") or 0) + restock_units,
                "return_damaged_units": int(req.get("return_damaged_units") or 0) + damaged_units,
                "return_refund_amount": cumulative_refund,
                "refund_status": refund_status,
                "reviewed_by": reviewer_email,
                "return_request_status": "processed",
                "stock_restored": bool(req.get("stock_restored")) or restock_units > 0,
            }
            , "$push": {"return_events": return_event}
        },
    )
    log_audit(
        "return_request",
        entity="purchase_requests",
        entity_id=request_id,
        details={
            "reason": reason,
            "condition": condition,
            "order_id": oid,
            "restock_units": restock_units,
            "damaged_units": damaged_units,
            "refund_amount": round(refund_total, 2),
        },
    )
    _record_request_event(
        db, request_id, "returned", actor_email=reviewer_email,
        details={
            "condition": condition, "restock_units": restock_units,
            "damaged_units": damaged_units, "refund_amount": round(refund_total, 2),
            "refund_status": refund_status,
        },
    )
    full = get_request(request_id) or {}
    _notify_request_status(full, "devuelta" if is_complete else "devolucion_parcial")
    return full


def request_customer_return(request_id: int, *, customer_email: str, reason: str) -> dict[str, Any]:
    """Registra la intención del cliente; inventario y reembolso esperan inspección interna."""
    db = get_db()
    clean_email = (customer_email or "").strip().lower()
    clean_reason = (reason or "").strip()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)})
    if not req:
        raise ValueError("not_found")
    if (req.get("client_email") or "").strip().lower() != clean_email:
        raise ValueError("forbidden")
    if req.get("status") not in {"entregada", "devolucion_parcial"}:
        raise ValueError("must_be_delivered")
    if req.get("return_request_status") == "pending":
        raise ValueError("return_already_requested")
    if len(clean_reason) < 5:
        raise ValueError("return_reason_required")
    now = datetime.now(timezone.utc).isoformat()
    db["purchase_requests"].update_one(
        {"request_id": int(request_id)},
        {"$set": {
            "return_request_status": "pending", "return_request_reason": clean_reason,
            "return_requested_at": now, "return_requested_by": clean_email,
        }},
    )
    _record_request_event(
        db, request_id, "return_requested", actor_email=clean_email,
        details={"reason": clean_reason},
    )
    notify_roles(
        roles=(ADMIN_ROLE, "vendedor"),
        subject=f"Devolución solicitada · pedido #{request_id}",
        body=f"{clean_email} solicita una devolución: {clean_reason}",
        category="ventas", meta={"request_id": int(request_id)},
    )
    return get_request(request_id) or {}


def list_store_products(*, category_id: int | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    active_categories = db["dim_categoria"].distinct("category_id", {"active": {"$ne": False}})
    query: dict[str, Any] = {
        "active": {"$ne": False},
        "category_id": {"$in": active_categories or [-1]},
    }
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
    if not db["dim_categoria"].find_one({"name": item_type, "active": {"$ne": False}}):
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
    sync_info: dict[str, Any] = {}
    try:
        from shared.analytics_sync import sync_order_to_fact

        sync_info = sync_order_to_fact(oid)
    except Exception as exc:
        sync_info = {"error": str(exc)}
    return {**doc, "analytics_sync": sync_info}


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
    try:
        from shared.analytics_sync import sync_order_to_fact

        sync_order_to_fact(order_id, force=True)
    except Exception:
        pass
    row = col.find_one({"order_id": str(order_id)}, {"_id": 0})
    return dict(row) if row else {}


def delete_order(order_id: str) -> int:
    col = sales_collection()
    n = col.count_documents({"order_id": str(order_id)})
    if not n:
        raise ValueError("not_found")
    col.delete_many({"order_id": str(order_id)})
    try:
        db = get_db()
        db["fact_ventas"].delete_many({"order_id": str(order_id)})
        try:
            db["fact_ventas"].delete_many({"order_id": int(order_id)})
        except (TypeError, ValueError):
            pass
    except Exception:
        pass
    log_audit("delete_order", entity="sales_records", entity_id=order_id, details={"deleted": n})
    return n
