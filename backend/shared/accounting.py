"""Núcleo contable: conciliación, cartera, cierres, facturas y notas de crédito."""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from shared.audit import log_audit
from shared.company_profile import get_company_profile
from shared.mongo import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(collection: str, field: str) -> int:
    row = get_db()[collection].find_one({}, {field: 1, "_id": 0}, sort=[(field, -1)])
    return int(row[field]) + 1 if row and row.get(field) is not None else 1


def format_invoice_number(year: int, sequence: int) -> str:
    return f"FAC-{int(year):04d}-{int(sequence):06d}"


def format_credit_note_number(year: int, sequence: int) -> str:
    return f"NC-{int(year):04d}-{int(sequence):06d}"


def period_bounds(period_type: str, value: str) -> tuple[str, str, str]:
    kind = (period_type or "").strip().lower()
    raw = (value or "").strip()
    try:
        if kind == "daily":
            parsed = date.fromisoformat(raw)
            iso = parsed.isoformat()
            return iso, iso, iso
        if kind == "monthly":
            parsed = datetime.strptime(raw, "%Y-%m").date()
            last = calendar.monthrange(parsed.year, parsed.month)[1]
            return raw, f"{raw}-01", f"{raw}-{last:02d}"
    except (TypeError, ValueError):
        pass
    raise ValueError("invalid_period")


def is_period_closed(at: str | date | datetime | None = None) -> bool:
    if isinstance(at, datetime):
        day = at.date().isoformat()
    elif isinstance(at, date):
        day = at.isoformat()
    else:
        day = str(at or date.today().isoformat())[:10]
    return bool(
        get_db()["accounting_periods"].find_one(
            {"status": "closed", "start_date": {"$lte": day}, "end_date": {"$gte": day}},
            {"_id": 1},
        )
    )


def assert_period_open(at: str | date | datetime | None = None) -> None:
    if is_period_closed(at):
        raise ValueError("accounting_period_closed")


def calculate_reconciliation(*, expected: float, paid: float, refunded: float, invoiced: float) -> dict[str, Any]:
    expected_n = round(float(expected or 0), 2)
    paid_n = round(float(paid or 0), 2)
    refunded_n = round(float(refunded or 0), 2)
    invoiced_n = round(float(invoiced or 0), 2)
    net_paid = round(paid_n - refunded_n, 2)
    balance = round(max(expected_n - net_paid, 0), 2)
    return {
        "expected": expected_n,
        "paid": paid_n,
        "refunded": refunded_n,
        "net_paid": net_paid,
        "invoiced": invoiced_n,
        "balance_due": balance,
        "reconciled": abs(expected_n - net_paid) < 0.01 and abs(expected_n - invoiced_n) < 0.01,
    }


def aging_bucket(due_date: str | date, *, as_of: date | None = None) -> tuple[str, int]:
    due = due_date if isinstance(due_date, date) else date.fromisoformat(str(due_date)[:10])
    days = ((as_of or date.today()) - due).days
    if days <= 0:
        return "not_due", max(days, 0)
    if days <= 30:
        return "1_30", days
    if days <= 60:
        return "31_60", days
    if days <= 90:
        return "61_90", days
    return "over_90", days


def request_due_date(req: dict[str, Any]) -> str:
    explicit = str(req.get("credit_due_date") or "")[:10]
    if explicit:
        return explicit
    created = date.fromisoformat(str(req.get("created_at") or date.today().isoformat())[:10])
    return (created + timedelta(days=max(int(req.get("credit_days") or 30), 1))).isoformat()


def get_or_create_invoice(request_doc: dict[str, Any], *, actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    request_id = int(request_doc["request_id"])
    existing = db["invoices"].find_one({"request_id": request_id}, {"_id": 0})
    if existing:
        return existing
    year = int(str(request_doc.get("created_at") or date.today().isoformat())[:4])
    sequence = _next_id("invoices", "invoice_id")
    total = round(float(request_doc.get("total") or request_doc.get("payment_due") or 0), 2)
    doc = {
        "invoice_id": sequence,
        "invoice_number": format_invoice_number(year, sequence),
        "request_id": request_id,
        "order_id": request_doc.get("order_id"),
        "client_email": request_doc.get("client_email"),
        "total": total,
        "currency": "USD",
        "status": "issued",
        "issued_at": _now(),
        "actor_email": actor_email,
    }
    db["invoices"].insert_one(doc)
    doc.pop("_id", None)
    log_audit("issue_invoice", entity="invoices", entity_id=sequence, details={"request_id": request_id})
    return doc


def reconcile_request(request_id: int) -> dict[str, Any]:
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    cash = list(db["cash_movements"].find({"request_id": int(request_id)}, {"_id": 0}))
    paid = sum(float(x.get("amount") or 0) for x in cash if x.get("movement_type") == "payment_in")
    refunded = sum(float(x.get("amount") or 0) for x in cash if x.get("movement_type") == "refund_out")
    invoice = db["invoices"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not invoice and req.get("status") in {"aprobada", "convertida", "enviada", "entregada"}:
        invoice = get_or_create_invoice(req)
    expected = float(req.get("total") or req.get("payment_due") or 0)
    calc = calculate_reconciliation(
        expected=expected,
        paid=paid,
        refunded=refunded,
        invoiced=float((invoice or {}).get("total") or 0),
    )
    return {"request_id": int(request_id), "order_id": req.get("order_id"), "invoice": invoice, **calc}


def list_receivables(*, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    query = {
        "status": {"$in": ["aprobada", "convertida", "enviada", "entregada"]},
        "payment_status": {"$ne": "pagado"},
    }
    rows = list(db["purchase_requests"].find(query, {"_id": 0}).sort("request_id", -1).limit(min(limit, 500)))
    out = []
    for req in rows:
        rec = reconcile_request(int(req["request_id"]))
        if rec["balance_due"] > 0:
            due_date = request_due_date(req)
            bucket, days_overdue = aging_bucket(due_date)
            out.append({
                "request_id": req["request_id"], "client_name": req.get("client_name"),
                "client_email": req.get("client_email"), "created_at": req.get("created_at"),
                "status": req.get("status"), "payment_status": req.get("payment_status"),
                "due_date": due_date, "aging_bucket": bucket, "days_overdue": days_overdue, **rec,
            })
    aging = {key: {"count": 0, "balance": 0.0} for key in ("not_due", "1_30", "31_60", "61_90", "over_90")}
    for row in out:
        item = aging[row["aging_bucket"]]
        item["count"] += 1
        item["balance"] = round(item["balance"] + row["balance_due"], 2)
    return {"receivables": out, "count": len(out), "total_due": round(sum(x["balance_due"] for x in out), 2), "aging": aging}


def customer_statement(email: str, *, limit: int = 200) -> dict[str, Any]:
    db = get_db()
    clean = (email or "").strip().lower()
    if not clean:
        raise ValueError("client_required")
    requests = list(db["purchase_requests"].find(
        {"client_email": {"$regex": f"^{__import__('re').escape(clean)}$", "$options": "i"}}, {"_id": 0}
    ).sort("request_id", -1).limit(min(limit, 500)))
    entries = []
    totals = {"charged": 0.0, "paid": 0.0, "refunded": 0.0, "balance": 0.0}
    for req in requests:
        rec = reconcile_request(int(req["request_id"]))
        due_date = request_due_date(req)
        bucket, days_overdue = aging_bucket(due_date)
        entry = {
            "request_id": int(req["request_id"]), "order_id": req.get("order_id"),
            "created_at": req.get("created_at"), "due_date": due_date,
            "aging_bucket": bucket, "days_overdue": days_overdue,
            "status": req.get("status"), "payment_status": req.get("payment_status"), **rec,
        }
        entries.append(entry)
        totals["charged"] += rec["expected"]
        totals["paid"] += rec["paid"]
        totals["refunded"] += rec["refunded"]
        totals["balance"] += rec["balance_due"]
    return {"client_email": clean, "entries": entries, "count": len(entries), "totals": {k: round(v, 2) for k, v in totals.items()}}


def record_partial_payment(
    request_id: int, *, amount: float, reference: str, actor_email: str | None = None,
    payment_method: str = "tarjeta",
) -> dict[str, Any]:
    assert_period_open()
    value = round(float(amount or 0), 2)
    clean_reference = (reference or "").strip()
    if value <= 0:
        raise ValueError("invalid_amount")
    if len(clean_reference) < 6:
        raise ValueError("reference_required")
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    if req.get("status") not in {"aprobada", "convertida", "enviada", "entregada"}:
        raise ValueError("approval_required_for_payment")
    if db["cash_movements"].find_one({"request_id": int(request_id), "reference": clean_reference, "movement_type": "payment_in"}):
        raise ValueError("duplicate_payment_reference")
    before = reconcile_request(int(request_id))
    if value > before["balance_due"] + 0.009:
        raise ValueError("payment_exceeds_balance")
    from shared.cash_ledger import record_cash_movement
    movement = record_cash_movement(
        movement_type="payment_in", amount=value, request_id=int(request_id),
        order_id=req.get("order_id"), payment_method=payment_method,
        actor_email=actor_email, reference=clean_reference, meta={"kind": "partial_payment"},
    )
    paid_total = round(before["net_paid"] + value, 2)
    settled = abs(before["balance_due"] - value) < 0.01
    patch = {
        "paid_amount": paid_total, "payment_status": "pagado" if settled else "parcial",
        "paid_at": date.today().isoformat() if settled else None,
        "last_payment_at": _now(), "last_payment_reference": clean_reference,
    }
    db["purchase_requests"].update_one({"request_id": int(request_id)}, {"$set": patch})
    log_audit("partial_payment", entity="purchase_requests", entity_id=request_id, details={"amount": value, "reference": clean_reference})
    return {"movement": movement, "reconciliation": reconcile_request(int(request_id)), **patch}


def margin_report(*, group_by: str = "product", limit: int = 100) -> dict[str, Any]:
    if group_by not in {"product", "customer", "channel", "country"}:
        raise ValueError("invalid_margin_group")
    db = get_db()
    requests = {int(r["request_id"]): r for r in db["purchase_requests"].find(
        {"status": {"$in": ["convertida", "enviada", "entregada"]}},
        {"_id": 0, "request_id": 1, "client_email": 1, "channel_id": 1, "country_id": 1},
    ).limit(5000)}
    channels = {int(r["channel_id"]): r.get("name") for r in db["dim_canal"].find({}, {"_id": 0, "channel_id": 1, "name": 1})}
    countries = {int(r["country_id"]): r.get("name") for r in db["dim_pais"].find({}, {"_id": 0, "country_id": 1, "name": 1})}
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "units": 0, "orders": set()})
    for line in db["purchase_request_lines"].find({"request_id": {"$in": list(requests)}}, {"_id": 0}).limit(20000):
        req = requests.get(int(line.get("request_id") or 0))
        if not req:
            continue
        if group_by == "product": key = str(line.get("product_name") or f"Producto {line.get('product_id')}")
        elif group_by == "customer": key = str(req.get("client_email") or "Sin cliente")
        elif group_by == "channel": key = str(channels.get(int(req.get("channel_id") or 0)) or "Sin canal")
        else: key = str(countries.get(int(req.get("country_id") or 0)) or "Sin país")
        qty = int(line.get("quantity") or 0)
        row = grouped[key]
        row["revenue"] += float(line.get("line_net") if line.get("line_net") is not None else float(line.get("unit_price") or 0) * qty)
        row["cost"] += float(line.get("unit_cost") or 0) * qty
        row["units"] += qty
        row["orders"].add(int(line["request_id"]))
    rows = []
    for label, values in grouped.items():
        revenue, cost = round(values["revenue"], 2), round(values["cost"], 2)
        rows.append({"label": label, "revenue": revenue, "cost": cost, "profit": round(revenue - cost, 2), "margin_pct": round((revenue - cost) / revenue * 100, 2) if revenue else 0.0, "units": values["units"], "orders": len(values["orders"])})
    rows.sort(key=lambda row: row["profit"], reverse=True)
    return {"group_by": group_by, "rows": rows[:min(limit, 500)], "count": len(rows)}


def financial_summary() -> dict[str, Any]:
    db = get_db()
    cash = list(db["cash_movements"].find({}, {"_id": 0}).limit(5000))
    income = sum(float(x.get("amount") or 0) for x in cash if x.get("movement_type") == "payment_in")
    refunds = sum(float(x.get("amount") or 0) for x in cash if x.get("movement_type") == "refund_out")
    lines = list(db["purchase_request_lines"].find({}, {"_id": 0, "quantity": 1, "unit_cost": 1}))
    costs = sum(float(x.get("unit_cost") or 0) * int(x.get("quantity") or 0) for x in lines)
    receivables = list_receivables(limit=500)
    net = round(income - refunds, 2)
    try:
        tax_rate = float(get_company_profile().get("tax_rate") or 0)
    except (TypeError, ValueError):
        tax_rate = 0.0
    tax = round(net * tax_rate / (100 + tax_rate), 2) if tax_rate > 0 else 0.0
    return {
        "income": round(income, 2), "refunds": round(refunds, 2), "net_cash": net,
        "costs": round(costs, 2), "gross_profit": round(net - costs, 2),
        "tax_included": tax, "tax_rate": tax_rate,
        "accounts_receivable": receivables["total_due"], "receivables_count": receivables["count"],
    }


def close_period(*, period_type: str, value: str, reason: str, actor_email: str | None = None) -> dict[str, Any]:
    key, start, end = period_bounds(period_type, value)
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 8:
        raise ValueError("reason_required")
    db = get_db()
    period_id = f"{period_type}:{key}"
    if db["accounting_periods"].find_one({"period_id": period_id, "status": "closed"}):
        raise ValueError("period_already_closed")
    doc = {
        "period_id": period_id, "period_type": period_type, "period": key,
        "start_date": start, "end_date": end, "status": "closed",
        "reason": clean_reason, "closed_by": actor_email, "closed_at": _now(),
        "snapshot": financial_summary(),
    }
    db["accounting_periods"].update_one({"period_id": period_id}, {"$set": doc}, upsert=True)
    log_audit("close_accounting_period", entity="accounting_periods", entity_id=period_id, details={"reason": clean_reason})
    return doc


def list_periods(*, limit: int = 50) -> list[dict[str, Any]]:
    return list(get_db()["accounting_periods"].find({}, {"_id": 0}).sort("closed_at", -1).limit(min(limit, 200)))


def create_credit_note(
    *, request_id: int, amount: float, reason: str, actor_email: str | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    assert_period_open()
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 8:
        raise ValueError("reason_required")
    value = round(float(amount or 0), 2)
    if value <= 0:
        raise ValueError("invalid_amount")
    db = get_db()
    req = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not req:
        raise ValueError("not_found")
    paid = float(req.get("paid_amount") or (req.get("total") if req.get("payment_status") == "pagado" else 0) or 0)
    previous = sum(float(x.get("amount") or 0) for x in db["credit_notes"].find({"request_id": int(request_id), "status": "issued"}, {"amount": 1}))
    if value > round(max(paid - previous, 0), 2):
        raise ValueError("credit_note_exceeds_paid")
    sequence = _next_id("credit_notes", "credit_note_id")
    year = date.today().year
    doc = {
        "credit_note_id": sequence, "credit_note_number": format_credit_note_number(year, sequence),
        "request_id": int(request_id), "order_id": req.get("order_id"), "amount": value,
        "currency": "USD", "reason": clean_reason, "status": "issued", "source": source,
        "issued_at": _now(), "actor_email": actor_email,
    }
    db["credit_notes"].insert_one(doc)
    from shared.cash_ledger import record_cash_movement
    record_cash_movement(
        movement_type="refund_out", amount=value, request_id=int(request_id),
        order_id=req.get("order_id"), actor_email=actor_email,
        reference=doc["credit_note_number"], meta={"credit_note_id": sequence, "reason": clean_reason},
    )
    doc.pop("_id", None)
    log_audit("issue_credit_note", entity="credit_notes", entity_id=sequence, details={"request_id": request_id, "amount": value})
    return doc


def list_credit_notes(*, limit: int = 100) -> list[dict[str, Any]]:
    return list(get_db()["credit_notes"].find({}, {"_id": 0}).sort("credit_note_id", -1).limit(min(limit, 500)))
