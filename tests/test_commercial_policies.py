from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from shared.commercial import customer_segment, discount_is_active, margin_percent, validate_checkout_policy
from pathlib import Path


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = [dict(row) for row in (rows or [])]

    def find_one(self, query=None, projection=None, **kwargs):
        query = query or {}
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return dict(row)
        return None

    def update_one(self, query, patch):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(patch.get("$set", {}))
                return type("Result", (), {"modified_count": 1})()
        return type("Result", (), {"modified_count": 0})()


class FakeDB:
    def __init__(self, **collections):
        self.collections = {name: FakeCollection(rows) for name, rows in collections.items()}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def test_margin_percent():
    assert margin_percent(revenue=100, cost=65) == 35.0
    assert margin_percent(revenue=0, cost=10) == 0.0


def test_discount_vigency():
    at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    assert discount_is_active({"active": True, "valid_from": "2026-08-01", "valid_to": "2026-08-31"}, at=at)
    assert not discount_is_active({"active": True, "valid_to": "2026-08-20"}, at=at)
    assert not discount_is_active({"active": False}, at=at)


def test_customer_segmentation():
    assert customer_segment(orders=0, spent=0) == "nuevo"
    assert customer_segment(orders=1, spent=80) == "ocasional"
    assert customer_segment(orders=3, spent=200) == "frecuente"
    assert customer_segment(orders=2, spent=5000) == "vip"


def test_commercial_admin_assets_are_wired():
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    js = root / "frontend" / "static" / "js" / "commercial-admin.js"
    css = root / "frontend" / "static" / "css" / "commercial-admin.css"
    assert 'id="page-commercial-admin"' in html
    assert 'data-page="commercial-admin"' in html
    assert "/static/js/commercial-admin.js" in html
    assert js.is_file() and css.is_file()


def test_checkout_policy_detects_all_commercial_limits():
    db = FakeDB(
        shop_settings=[{"shop_id": 1, "minimum_order_amount": 100, "maximum_order_amount": 500, "minimum_margin_pct": 30}],
        customers=[{"email": "cliente@test.com", "purchase_limit": 200}],
    )
    with pytest.raises(ValueError, match="minimum_order"):
        validate_checkout_policy(db, email="cliente@test.com", subtotal=80, discount=0, lines=[{"quantity": 1, "unit_cost": 60}])
    with pytest.raises(ValueError) as exc:
        validate_checkout_policy(db, email="cliente@test.com", subtotal=550, discount=0, lines=[{"quantity": 1, "unit_cost": 450}])
    assert {"maximum_order", "customer_limit", "minimum_margin"}.issubset(set(str(exc.value).split(":", 1)[1].split(",")))


def test_exception_only_authorizes_approved_scope_and_amount():
    settings = [{"shop_id": 1, "maximum_order_amount": 100, "minimum_margin_pct": 0}]
    customer = [{"email": "cliente@test.com"}]
    approved = [{"exception_id": 7, "status": "approved", "customer_email": "cliente@test.com", "amount": 150, "violations": ["maximum_order"]}]
    db = FakeDB(shop_settings=settings, customers=customer, commercial_exceptions=approved)
    policy = validate_checkout_policy(db, email="cliente@test.com", subtotal=120, discount=0, lines=[{"quantity": 1, "unit_cost": 80}], exception_id=7)
    assert policy["exception_id"] == 7

    db.collections["commercial_exceptions"].rows[0]["violations"] = ["minimum_margin"]
    with pytest.raises(ValueError, match="commercial_exception_required"):
        validate_checkout_policy(db, email="cliente@test.com", subtotal=120, discount=0, lines=[{"quantity": 1, "unit_cost": 80}], exception_id=7)
    db.collections["commercial_exceptions"].rows[0].update({"violations": ["maximum_order"], "amount": 110})
    with pytest.raises(ValueError, match="commercial_exception_required"):
        validate_checkout_policy(db, email="cliente@test.com", subtotal=120, discount=0, lines=[{"quantity": 1, "unit_cost": 80}], exception_id=7)


def test_exception_cannot_be_reused_after_consumption():
    from shared.commercial import mark_exception_used

    db = FakeDB(
        shop_settings=[{"shop_id": 1, "maximum_order_amount": 100}],
        customers=[{"email": "cliente@test.com"}],
        commercial_exceptions=[{"exception_id": 8, "status": "approved", "customer_email": "cliente@test.com", "amount": 150, "violations": ["maximum_order"]}],
    )
    mark_exception_used(db, 8, request_id=44)
    assert db["commercial_exceptions"].rows[0]["status"] == "used"
    with pytest.raises(ValueError, match="commercial_exception_required"):
        validate_checkout_policy(db, email="cliente@test.com", subtotal=120, discount=0, lines=[{"quantity": 1, "unit_cost": 80}], exception_id=8)


def test_coupon_vigency_minimum_and_segment():
    from paquetes.shop.services import _apply_coupon

    today = datetime.now(timezone.utc).date()
    base = {"code": "VIP10", "active": True, "value_type": "percentage", "value": 10, "usage_count": 0, "usage_limit": 5, "minimum_order_amount": 100, "allowed_segments": ["vip"]}
    db = FakeDB(discount_codes=[base], customers=[{"email": "vip@test.com", "segment": "vip"}, {"email": "nuevo@test.com", "segment": "nuevo"}])
    amount, _ = _apply_coupon(db, "VIP10", 200, "vip@test.com")
    assert amount == 20
    with pytest.raises(ValueError, match="coupon_minimum_order"):
        _apply_coupon(db, "VIP10", 50, "vip@test.com")
    with pytest.raises(ValueError, match="coupon_segment_restricted"):
        _apply_coupon(db, "VIP10", 200, "nuevo@test.com")
    db.collections["discount_codes"].rows[0]["valid_from"] = (today + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="coupon_not_current"):
        _apply_coupon(db, "VIP10", 200, "vip@test.com")
    db.collections["discount_codes"].rows[0].update({"valid_from": None, "valid_to": (today - timedelta(days=1)).isoformat()})
    with pytest.raises(ValueError, match="coupon_not_current"):
        _apply_coupon(db, "VIP10", 200, "vip@test.com")


def test_credit_enabled_disabled_and_limit():
    from paquetes.ventas.services import validate_credit_exposure

    with pytest.raises(ValueError, match="credit_not_enabled"):
        validate_credit_exposure({"credit_enabled": False, "credit_limit": 500}, current_exposure=0, requested=100)
    assert validate_credit_exposure({"credit_enabled": True, "credit_limit": 500}, current_exposure=200, requested=300) == 500
    with pytest.raises(ValueError, match="credit_limit_exceeded"):
        validate_credit_exposure({"credit_enabled": True, "credit_limit": 500}, current_exposure=200, requested=301)


def test_checkout_route_returns_409_for_commercial_policy(monkeypatch):
    from frontend.app import app
    from paquetes.shop import services

    monkeypatch.setattr(services, "create_checkout_from_cart", lambda data: (_ for _ in ()).throw(ValueError("commercial_exception_required:minimum_margin")))
    client = app.test_client()
    with client.session_transaction() as session:
        session.update({"user_id": "admin", "email": "admin@test.com", "name": "Admin", "role": "administrador"})
    response = client.post("/api/shop/checkout", json={"lines": [{"variant_id": 1, "quantity": 1}]})
    assert response.status_code == 409
    assert response.get_json()["violations"] == ["minimum_margin"]


def test_coupon_usage_limit_is_atomic():
    from paquetes.shop.services import _claim_coupon_usage
    from shared.mongo import get_db

    db = get_db()
    code = "TEST-CONCURRENT-COUPON"
    db["discount_codes"].delete_many({"code": code})
    db["discount_codes"].insert_one({"discount_id": 990001, "code": code, "active": True, "usage_limit": 1, "usage_count": 0})
    try:
        def claim(_):
            try:
                _claim_coupon_usage(db, code)
                return "ok"
            except ValueError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, range(2)))
        assert results.count("ok") == 1
        assert results.count("coupon_exhausted") == 1
        assert db["discount_codes"].find_one({"code": code})["usage_count"] == 1
    finally:
        db["discount_codes"].delete_many({"code": code})
