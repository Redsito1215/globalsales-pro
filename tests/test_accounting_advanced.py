from __future__ import annotations

from datetime import date, timedelta

import pytest


def _db():
    from shared.mongo import get_db, mongo_client
    db = get_db()
    mongo_client().admin.command("ping")
    return db


def test_aging_bucket_boundaries():
    from shared.accounting import aging_bucket

    today = date(2026, 8, 24)
    assert aging_bucket(today + timedelta(days=5), as_of=today)[0] == "not_due"
    assert aging_bucket(today - timedelta(days=1), as_of=today) == ("1_30", 1)
    assert aging_bucket(today - timedelta(days=31), as_of=today) == ("31_60", 31)
    assert aging_bucket(today - timedelta(days=61), as_of=today) == ("61_90", 61)
    assert aging_bucket(today - timedelta(days=91), as_of=today) == ("over_90", 91)


def test_partial_payments_update_balance_and_status(monkeypatch):
    from shared import accounting

    db = _db()
    request_id = 990101
    email = "accounting-test@globtrade.test"
    cleanup = {"request_id": request_id}
    for name in ("purchase_requests", "cash_movements", "invoices", "audit_log"):
        db[name].delete_many(cleanup if name != "audit_log" else {"entity_id": request_id})
    db["purchase_requests"].insert_one({
        "request_id": request_id, "client_name": "Prueba Contable", "client_email": email,
        "status": "aprobada", "payment_status": "credito", "total": 100.0,
        "payment_due": 100.0, "created_at": date.today().isoformat(),
    })
    monkeypatch.setattr(accounting, "assert_period_open", lambda *args, **kwargs: None)
    try:
        first = accounting.record_partial_payment(request_id, amount=40, reference="ABONO-001", actor_email="admin@test.com")
        assert first["payment_status"] == "parcial"
        assert first["reconciliation"]["balance_due"] == 60
        with pytest.raises(ValueError, match="duplicate_payment_reference"):
            accounting.record_partial_payment(request_id, amount=5, reference="ABONO-001")
        second = accounting.record_partial_payment(request_id, amount=60, reference="ABONO-002", actor_email="admin@test.com")
        assert second["payment_status"] == "pagado"
        assert second["reconciliation"]["balance_due"] == 0
        row = db["purchase_requests"].find_one({"request_id": request_id})
        assert row["paid_amount"] == 100
    finally:
        for name in ("purchase_requests", "cash_movements", "invoices"):
            db[name].delete_many(cleanup)
        db["audit_log"].delete_many({"entity_id": request_id})


def test_customer_statement_consolidates_charges_and_payments(monkeypatch):
    from shared import accounting

    db = _db()
    request_id = 990102
    email = "statement-test@globtrade.test"
    db["purchase_requests"].delete_many({"request_id": request_id})
    db["cash_movements"].delete_many({"request_id": request_id})
    db["invoices"].delete_many({"request_id": request_id})
    db["purchase_requests"].insert_one({
        "request_id": request_id, "client_email": email, "client_name": "Estado Cuenta",
        "status": "aprobada", "payment_status": "parcial", "total": 80.0,
        "payment_due": 80.0, "created_at": date.today().isoformat(),
    })
    monkeypatch.setattr(accounting, "assert_period_open", lambda *args, **kwargs: None)
    try:
        accounting.record_partial_payment(request_id, amount=30, reference="ESTADO-001")
        statement = accounting.customer_statement(email)
        assert statement["count"] == 1
        assert statement["totals"] == {"charged": 80.0, "paid": 30.0, "refunded": 0.0, "balance": 50.0}
    finally:
        db["purchase_requests"].delete_many({"request_id": request_id})
        db["cash_movements"].delete_many({"request_id": request_id})
        db["invoices"].delete_many({"request_id": request_id})


def test_margin_report_groups_commercial_dimensions():
    from shared.accounting import margin_report

    db = _db()
    request_id = 990103
    db["purchase_requests"].delete_many({"request_id": request_id})
    db["purchase_request_lines"].delete_many({"request_id": request_id})
    db["purchase_requests"].insert_one({
        "request_id": request_id, "status": "convertida", "client_email": "margin-test@globtrade.test",
        "channel_id": 1, "country_id": 1,
    })
    db["purchase_request_lines"].insert_one({
        "line_id": 990103, "request_id": request_id, "product_id": 990103,
        "product_name": "Producto Margen Integración", "quantity": 2,
        "unit_price": 500000.0, "unit_cost": 100000.0, "line_net": 1000000.0,
    })
    try:
        product = margin_report(group_by="product", limit=500)
        row = next(item for item in product["rows"] if item["label"] == "Producto Margen Integración")
        assert row["profit"] == 800000
        assert row["margin_pct"] == 80
        customer = margin_report(group_by="customer", limit=500)
        assert any(item["label"] == "margin-test@globtrade.test" for item in customer["rows"])
    finally:
        db["purchase_requests"].delete_many({"request_id": request_id})
        db["purchase_request_lines"].delete_many({"request_id": request_id})
