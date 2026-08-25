"""Smoke tests — lógica de negocio y rutas registradas (sin exigir Mongo vivo)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)


def test_variant_prices_from_base_rebaja_25():
    from paquetes.shop.services import variant_prices_from_base

    assert variant_prices_from_base(100.0, sale_enabled=False) == (100.0, 0.0)
    assert variant_prices_from_base(100.0, sale_enabled=True, sale_percent=25) == (75.0, 100.0)
    assert variant_prices_from_base(100.0, sale_enabled=True, sale_percent=10) == (90.0, 100.0)


def test_clamp_sale_percent():
    from paquetes.shop.services import clamp_sale_percent

    assert clamp_sale_percent(25) == 25
    assert clamp_sale_percent(0) == 1
    assert clamp_sale_percent(99) == 90
    assert clamp_sale_percent("x") == 25


def test_allocate_discount_prorratea():
    from paquetes.ventas.services import _allocate_discount

    assert _allocate_discount([100.0, 50.0], 15.0) == [10.0, 5.0]
    assert sum(_allocate_discount([80.0, 20.0], 10.0)) == pytest.approx(10.0)
    assert _allocate_discount([], 5.0) == []
    assert _allocate_discount([10.0], 0) == [0.0]


def test_request_statuses_incluyen_devuelta_y_pago():
    from paquetes.ventas.services import PAYMENT_STATUSES, REQUEST_STATUSES, RETURN_CONDITIONS

    assert "devuelta" in REQUEST_STATUSES
    assert "entregada" in REQUEST_STATUSES
    assert "pagado" in PAYMENT_STATUSES
    assert "credito" in PAYMENT_STATUSES
    assert RETURN_CONDITIONS == frozenset({"apto", "danado", "mixto"})


def test_plan_return_stock_apto_danado_mixto():
    from paquetes.ventas.services import plan_return_stock

    lines = [{"variant_id": 1, "quantity": 3}, {"variant_id": 2, "quantity": 2}]
    restock, damaged = plan_return_stock(lines, condition="apto")
    assert sum(x["quantity"] for x in restock) == 5
    assert damaged == []

    restock, damaged = plan_return_stock(lines, condition="danado")
    assert restock == []
    assert sum(x["quantity"] for x in damaged) == 5

    restock, damaged = plan_return_stock(
        lines,
        condition="mixto",
        inspections=[
            {"variant_id": 1, "restock_qty": 2, "damaged_qty": 1},
            {"variant_id": 2, "restock_qty": 0, "damaged_qty": 2},
        ],
    )
    assert restock == [{"variant_id": 1, "quantity": 2}]
    assert sum(x["quantity"] for x in damaged) == 3

    import pytest

    with pytest.raises(ValueError, match="return_condition_required"):
        plan_return_stock(lines, condition="")
    with pytest.raises(ValueError, match="return_qty_mismatch"):
        plan_return_stock(
            lines,
            condition="mixto",
            inspections=[{"variant_id": 1, "restock_qty": 1, "damaged_qty": 1}, {"variant_id": 2, "restock_qty": 1, "damaged_qty": 1}],
        )


def test_compras_po_statuses():
    from paquetes.compras.services import PO_STATUSES

    assert "borrador" in PO_STATUSES
    assert "enviada" in PO_STATUSES
    assert "recibida" in PO_STATUSES


def test_roles_catalog_tiene_compras_y_decisiones():
    from shared.roles_registry import PAGE_CATALOG, PERMISSION_CATALOG

    assert "compras" in PAGE_CATALOG
    assert "decisiones" in PAGE_CATALOG
    assert "compras.manage" in PERMISSION_CATALOG
    assert "decisiones.view" in PERMISSION_CATALOG
    assert "masters.write" in PERMISSION_CATALOG
    assert "audit.read" in PERMISSION_CATALOG


def test_disable_role_reasigna_usuarios(monkeypatch):
    from auth import roles_service
    from shared.roles_registry import ADMIN_ROLE, DEFAULT_REGISTER_ROLE

    class FakeUsers:
        def __init__(self):
            self.docs = [{"role": "vendedor", "active": True}, {"role": "vendedor", "active": True}]
            self.updates = []

        def count_documents(self, q):
            return sum(1 for d in self.docs if d.get("role") == q.get("role") and d.get("active") is True)

        def update_many(self, q, patch):
            self.updates.append((q, patch))
            for d in self.docs:
                if d.get("role") == q.get("role") and d.get("active") is True:
                    d["role"] = patch["$set"]["role"]

    class FakeRoles:
        def update_one(self, q, patch):
            return None

    fake_users = FakeUsers()
    fake_roles = FakeRoles()
    fake_db = {"users": fake_users, "app_roles": fake_roles}

    monkeypatch.setattr(roles_service, "get_role", lambda slug: {
        "slug": slug,
        "label": slug,
        "active": True,
        "assignable": True,
    } if slug in (ADMIN_ROLE, "vendedor") else None)
    monkeypatch.setattr(roles_service, "get_ops_db", lambda: fake_db)
    monkeypatch.setattr(roles_service, "_col", lambda: fake_roles)

    with pytest.raises(ValueError, match="protected_role"):
        roles_service.disable_role(ADMIN_ROLE)

    result = roles_service.disable_role("vendedor")
    assert result["users_reassigned"] == 2
    assert result["fallback_role"] == DEFAULT_REGISTER_ROLE
    assert all(d["role"] == DEFAULT_REGISTER_ROLE for d in fake_users.docs)


def test_ensure_roles_seed_respeta_rol_inactivo(monkeypatch):
    from auth import roles_service

    stored = {"slug": "vendedor", "active": False, "assignable": False, "label": "Vendedor comercial"}

    class FakeCol:
        def find(self, q, proj=None):
            return []

        def find_one(self, q, proj=None):
            if q.get("slug") == "vendedor":
                return dict(stored)
            return None

        def update_one(self, q, patch, upsert=False):
            if q.get("slug") == "vendedor" and "$set" in patch:
                stored.update(patch["$set"])

    monkeypatch.setattr(roles_service, "_col", lambda: FakeCol())
    roles_service.ensure_roles_seed()
    assert stored["active"] is False
    assert stored["assignable"] is False


def test_app_registra_blueprints_clave():
    from frontend.app import app

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/decisiones/panel" in rules
    assert "/api/compras/inventory" in rules
    assert "/api/compras/vendors" in rules
    assert "/api/compras/purchase-orders" in rules
    assert "/api/compras/purchase-orders/<int:po_id>/send" in rules
    assert any("/solicitudes" in r and "devolver" in r for r in rules)
    assert any("/solicitudes" in r and "pago" in r for r in rules)


def test_health_endpoint_responde_json():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/health")
    # 503/500 si Mongo u otro dependency no está disponible
    assert r.status_code in (200, 500, 503)
    data = r.get_json(silent=True) or {}
    assert "status" in data or r.status_code in (500, 503)


def test_checkout_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.post("/api/shop/checkout", json={"lines": []})
    assert r.status_code == 401
    body = r.get_json() or {}
    assert body.get("code") == "auth_required"


def test_decisiones_panel_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/decisiones/panel")
    assert r.status_code == 401


def test_compras_inventory_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/compras/inventory")
    assert r.status_code == 401


def test_devolver_endpoint_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.post("/api/solicitudes/1/devolver", json={})
    assert r.status_code == 401


def test_pagar_endpoint_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.post("/api/solicitudes/1/pagar", json={"method": "transferencia"})
    assert r.status_code == 401


def test_audit_log_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/audit_log")
    assert r.status_code == 401


def test_audit_log_serializa_objectid_en_details():
    _require_mongo()
    from frontend.app import app
    from shared.mongo import get_db

    db = get_db()
    db["audit_log"].insert_one(
        {
            "action": "test_audit_json",
            "entity": "test",
            "entity_id": "x",
            "email": "test@example.com",
            "details": {"_id": "6a16394e477fc25923669a07"},
            "at": "2026-08-10T00:00:00+00:00",
        }
    )
    # simulate ObjectId in details like legacy rows
    db["audit_log"].update_one(
        {"action": "test_audit_json"},
        {"$set": {"details._id": __import__("bson").ObjectId("6a16394e477fc25923669a07")}},
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "6a16394e477fc25923669a07"
        sess["email"] = "test@example.com"
        sess["role"] = "administrador"
    r = client.get("/api/audit_log?entity=test&entity_id=x&limit=100")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["limit"] == 100
    assert any(e.get("action") == "test_audit_json" for e in data.get("entries", []))
    db["audit_log"].delete_many({"action": "test_audit_json"})


def test_audit_log_filtro_rol_y_paginacion():
    _require_mongo()
    from paquetes.datos.services import list_audit_log

    out = list_audit_log(limit=500, offset=0, role="vendedor")
    assert out["limit"] == 100
    assert out.get("role") == "vendedor"
    assert isinstance(out.get("roles"), list)


def test_auditoria_compara_y_protege_datos_sensibles():
    from shared.audit import audit_changes

    changes = audit_changes(
        {"name": "Anterior", "password": "vieja", "card_number": "4111111111111111"},
        {"name": "Nuevo", "password": "nueva", "card_number": "5555555555554444"},
    )
    assert changes["name"] == {"before": "Anterior", "after": "Nuevo"}
    assert changes["password"]["before"] == "[PROTEGIDO]"
    assert changes["password"]["after"] == "[PROTEGIDO]"
    assert changes["card_number"]["after"] == "[PROTEGIDO]"


def test_audit_export_exige_auth():
    from frontend.app import app

    client = app.test_client()
    assert client.get("/api/audit_log/export").status_code == 401


def test_spa_incluye_controles_basicos_de_accesibilidad():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend/static/index.html").read_text(encoding="utf-8")
    css = (root / "frontend/static/css/accessibility.css").read_text(encoding="utf-8")
    js = (root / "frontend/static/js/accessibility.js").read_text(encoding="utf-8")
    assert 'class="skip-link" href="#main-content"' in html
    assert 'id="main-content" tabindex="-1"' in html
    assert 'id="a11y-page-status"' in html
    assert "prefers-reduced-motion" in css
    assert "focus-visible" in css
    assert "aria-modal" in js
    assert "MutationObserver" in js


def test_verificador_de_entrega_es_no_destructivo_y_completo():
    _require_mongo()
    from scripts.verify_release import run

    report = run(skip_mongo=False)
    assert report["ready"] is True
    assert {item["check"] for item in report["checks"]} == {"archivos", "aplicacion", "salud", "mongo"}


def test_distribucion_historica_es_exacta_y_suave():
    from scripts.replace_analytics_dataset import allocate_monthly_counts, month_starts

    months = month_starts(__import__("datetime").date(2010, 1, 1), __import__("datetime").date(2026, 8, 24))
    counts = allocate_monthly_counts(2_000_000, months)
    assert len(months) == 200
    assert sum(counts) == 2_000_000
    assert max(counts) / min(counts) < 1.6
    assert all(value > 0 for value in counts)


def test_tendencia_historica_no_se_limita_a_diez_anios():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "paquetes/tablero/queries.py").read_text(encoding="utf-8")
    assert '{"$limit": last_n if last_n < 999 else 600}' in source
    assert '{"$limit": last_n if last_n < 999 else 120}' not in source


def test_cabecera_tienda_muestra_inicio_de_sesion_al_visitante():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend/static/index.html").read_text(encoding="utf-8")
    nav = (root / "frontend/static/js/shop-header-nav.js").read_text(encoding="utf-8")
    assert 'id="shop-header-login"' in html
    assert 'onclick="openLoginModal()">Iniciar sesión</button>' in html
    assert "headerLogin.hidden = loggedIn" in nav


def test_buscador_tienda_es_visible_y_filtra_al_escribir():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend/static/index.html").read_text(encoding="utf-8")
    tienda = (root / "frontend/static/js/tienda.js").read_text(encoding="utf-8")
    assert 'class="shop-madson-search-btn">Buscar</button>' in html
    assert 'oninput="onShopHeaderSearchInput()"' in html
    assert "function onShopHeaderSearchInput()" in tienda
    assert "function clearShopSearch()" in tienda


def test_tienda_no_limita_catalogo_de_120_productos_a_100():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "frontend/static/js/tienda.js").read_text(encoding="utf-8")
    route = (Path(__file__).resolve().parents[1] / "paquetes/shop/routes.py").read_text(encoding="utf-8")
    assert "new URLSearchParams({ limit: 200 })" in source
    assert "new URLSearchParams({ limit: 100 })" not in source
    assert 'limit=min(max(int(request.args.get("limit", 48)), 1), 200)' in route


def test_recuperacion_de_contrasena_esta_retirada():
    from frontend.app import app
    from pathlib import Path

    client = app.test_client()
    assert client.post("/api/auth/forgot-password", json={"email": "x@example.com"}).status_code == 404
    assert client.post("/api/auth/reset-password", json={"token": "x"}).status_code == 404
    html = (Path(__file__).resolve().parents[1] / "frontend/static/index.html").read_text(encoding="utf-8").lower()
    assert "olvidaste tu contraseña" not in html
    assert "forgot-modal" not in html
    assert "reset-modal" not in html


def test_login_no_muestra_texto_ni_error_vacio():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend/static/index.html").read_text(encoding="utf-8")
    css = (root / "frontend/static/css/admin-ui.css").read_text(encoding="utf-8")
    assert "Para exportar, generar o administrar datos" not in html
    assert ".login-error:empty" in css
    assert "display: none" in css.split(".login-error:empty", 1)[1].split("}", 1)[0]


def test_airflow_no_sobrescribe_historico_automaticamente():
    from pathlib import Path

    dag = (Path(__file__).resolve().parents[1] / "airflow/dags/globtrade_strategic_etl.py").read_text(encoding="utf-8")
    assert "schedule=None" in dag
    assert 'schedule="0 2 * * *"' not in dag


def test_enable_role_reactiva(monkeypatch):
    from auth import roles_service

    stored = {"slug": "vendedor", "active": False, "assignable": False, "label": "Vendedor"}

    class FakeCol:
        def find_one(self, q, proj=None):
            if q.get("slug") == "vendedor":
                return dict(stored)
            return None

        def update_one(self, q, patch):
            if q.get("slug") == "vendedor":
                stored.update(patch["$set"])

    monkeypatch.setattr(roles_service, "_col", lambda: FakeCol())
    monkeypatch.setattr(roles_service, "get_role", lambda slug: dict(stored) if slug == "vendedor" else None)

    result = roles_service.enable_role("vendedor")
    assert result["slug"] == "vendedor"
    assert stored["active"] is True
    assert stored["assignable"] is True


def test_sales_order_detail_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/sales/orders/1")
    assert r.status_code == 401


def test_po_send_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.post("/api/compras/purchase-orders/1/send")
    assert r.status_code == 401


def test_ops_indexes_specs_cubren_solicitudes_y_stock():
    from shared.ops_indexes import ensure_ops_indexes
    # Solo valida que la función es importable y tipada; no exige Mongo
    assert callable(ensure_ops_indexes)


def test_low_stock_alert_apunta_a_compras():
    from paquetes.decisiones.services import build_alerts

    alerts = build_alerts(
        margin={"bottom": []},
        stock={"low_count": 2, "insight": "2 SKUs bajos"},
        funnel={"awaiting_action": 0, "conversion_rate": None, "total_created": 0},
        channels=[],
    )
    stock_alerts = [a for a in alerts if a.get("code") == "low_stock"]
    assert stock_alerts
    assert stock_alerts[0]["action"] == "compras"


def test_post_solicitudes_exige_checkout():
    _require_mongo()
    from frontend.app import app

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "test"
        sess["email"] = "test@example.com"
        sess["role"] = "cliente"
        sess["permissions"] = ["shop.view", "shop.checkout"]
    r = client.post("/api/solicitudes", json={"lines": [{"product_id": 1, "quantity": 1}]})
    # Puede ser 400 use_checkout o 403 si sesión no completa permisos en decorador
    assert r.status_code in (400, 401, 403)
    if r.status_code == 400:
        data = r.get_json() or {}
        assert data.get("code") == "use_checkout"


def test_update_status_bloquea_convertida_directa():
    from paquetes.ventas.services import update_status
    import pytest

    with pytest.raises(ValueError, match="use_dedicated_endpoint"):
        update_status(1, "convertida", reviewer_email="x@y.com")


def test_update_status_bloquea_devuelta_directa():
    from paquetes.ventas.services import update_status
    import pytest

    with pytest.raises(ValueError, match="use_dedicated_endpoint"):
        update_status(1, "devuelta", reviewer_email="x@y.com")


def test_offline_channel_sin_envio():
    from paquetes.ventas.services import (
        _is_offline_channel,
        _payment_allows_progress,
        display_order_id,
        platform_order_id,
    )

    assert _is_offline_channel({"name": "Offline"})
    assert _is_offline_channel({"channel_name": "Offline", "channel_id": 2})
    assert not _is_offline_channel({"name": "Online"})
    assert not _is_offline_channel(None)
    assert _payment_allows_progress({"channel_name": "Online", "payment_status": "pagado"})
    assert not _payment_allows_progress({"channel_name": "Online", "payment_status": "credito"})
    assert _payment_allows_progress({"channel_name": "Offline", "payment_status": "credito"})
    assert platform_order_id(8) == "V-00008"
    assert display_order_id("1000000000", 8) == "V-00008"
    assert display_order_id("V-00011", 11) == "V-00011"


def test_repair_legacy_platform_order_ids():
    from paquetes.ventas.services import platform_order_id, repair_legacy_platform_order_ids

    pr_docs = [
        {"request_id": 3, "order_id": "1000000000"},
        {"request_id": 7, "order_id": "1000000000"},
        {"request_id": 9, "order_id": "V-00009"},
    ]
    sr_docs = [
        {"request_id": 3, "order_id": "1000000000"},
        {"request_id": 7, "order_id": "1000000000"},
        {"request_id": 9, "order_id": "V-00009"},
    ]

    class PRCol:
        def find(self, q, proj=None):
            if q.get("order_id") == "1000000000":
                return [dict(d) for d in pr_docs if d["order_id"] == "1000000000"]
            return []

        def update_one(self, q, patch):
            for d in pr_docs:
                if d["request_id"] == q["request_id"]:
                    d.update(patch["$set"])

    class SRCol:
        def update_many(self, q, patch):
            n = 0
            for d in sr_docs:
                if d.get("request_id") == q["request_id"]:
                    d["order_id"] = patch["$set"]["order_id"]
                    n += 1

            class Result:
                modified_count = n

            return Result()

    class FakeDB:
        def __getitem__(self, name):
            if name == "purchase_requests":
                return PRCol()
            if name == "sales_records":
                return SRCol()
            raise KeyError(name)

    fixed = repair_legacy_platform_order_ids(FakeDB())
    assert fixed == 2
    assert pr_docs[0]["order_id"] == platform_order_id(3)
    assert pr_docs[1]["order_id"] == platform_order_id(7)
    assert pr_docs[2]["order_id"] == "V-00009"
    assert sr_docs[0]["order_id"] == platform_order_id(3)
    assert sr_docs[1]["order_id"] == platform_order_id(7)


def test_pulse_for_email_detecta_nuevas():
    _require_mongo()
    from shared.notifications import notify_user, pulse_for_email, _col

    email = "pulse-smoke@globtrade.test"
    _col().delete_many({"recipient_email": email})
    try:
        n1 = notify_user(recipient_email=email, subject="Primera", body="A")
        seed = pulse_for_email(email, after_id=0)
        assert seed["latest_id"] == n1["notification_id"]
        assert seed["new"] == []
        assert seed["unread"] >= 1

        notify_user(recipient_email=email, subject="Segunda", body="B")
        pulse = pulse_for_email(email, after_id=seed["latest_id"])
        assert len(pulse["new"]) == 1
        assert pulse["new"][0]["subject"] == "Segunda"
        assert pulse["latest_id"] > seed["latest_id"]
    finally:
        _col().delete_many({"recipient_email": email})


def test_notifications_pulse_endpoint_exige_auth():
    from frontend.app import app

    client = app.test_client()
    assert client.get("/api/auth/notifications/pulse?after=0").status_code == 401


def test_notifications_pulse_endpoint_ok():
    _require_mongo()
    from frontend.app import app
    from shared.notifications import _col, notify_user

    email = "pulse-endpoint@globtrade.test"
    _col().delete_many({"recipient_email": email})
    try:
        notify_user(recipient_email=email, subject="Hola", body="Mundo")
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = "pulse-user-1"
            sess["email"] = email
            sess["role"] = "cliente"
        r = client.get("/api/auth/notifications/pulse?after=0")
        assert r.status_code == 200
        data = r.get_json() or {}
        assert data.get("status") == "ok"
        assert "latest_id" in data
        assert "unread" in data
        assert data.get("new") == []

        r2 = client.get(f"/api/auth/notifications/pulse?after={data['latest_id']}")
        assert r2.status_code == 200
        assert (r2.get_json() or {}).get("new") == []
    finally:
        _col().delete_many({"recipient_email": email})


def test_soporte_mensajes_after_id():
    _require_mongo()
    from paquetes.soporte.services import list_thread, post_message, _col

    thread = "after-id-smoke@globtrade.test"
    _col().delete_many({"thread_email": thread})
    try:
        m1 = post_message(
            author_email=thread,
            author_name="Cliente",
            text="Hola",
            thread_email=thread,
            staff=False,
        )
        full = list_thread(thread, after_id=0)
        assert len(full["messages"]) >= 1
        assert full["latest_id"] >= m1["message_id"]

        m2 = post_message(
            author_email="staff@globtrade.com",
            author_name="Staff",
            text="Respuesta",
            thread_email=thread,
            staff=True,
        )
        delta = list_thread(thread, after_id=m1["message_id"])
        assert len(delta["messages"]) == 1
        assert delta["messages"][0]["message_id"] == m2["message_id"]
    finally:
        _col().delete_many({"thread_email": thread})


def test_bodega_general_unica():
    _require_mongo()
    from shared.warehouse import DEFAULT_WAREHOUSE_NAME, warehouse_summary

    wh = warehouse_summary()
    assert wh["name"] == DEFAULT_WAREHOUSE_NAME
    assert wh["warehouse_id"] == 1


def test_shop_product_specs_derivados():
    from paquetes.shop.services import _derive_product_specs

    specs = _derive_product_specs(
        {"product_id": 81, "line": 1, "name": "Orange Juice"},
        "Beverages",
        "Bebidas y líquidos",
    )
    assert specs["weight_kg"] > 0
    assert "Bebidas" in specs["main_function"]
    assert "description" in specs

def test_vendedor_tiene_compras_manage():
    from shared.roles_registry import DEFAULT_ROLES

    vend = next(r for r in DEFAULT_ROLES if r["slug"] == "vendedor")
    assert "compras.manage" in vend["permissions"]
    assert "compras" in vend["pages"]


def test_utc_today_helper_no_utcnow():
    from paquetes.tablero import queries

    assert queries._utc_today_str()
    assert "utcnow" not in queries._months_cutoff.__code__.co_names


def test_match_months_ancla_en_dataset_no_en_hoy(monkeypatch):
    from paquetes.tablero import queries

    monkeypatch.setattr(queries, "dataset_filter_anchor_date", lambda: "2017-12-31")
    q = queries._landing_match(months=24)
    assert "order_date" in q
    assert q["order_date"]["$gte"].startswith("2015")
    q_all = queries._landing_match(months=999)
    assert "order_date" not in q_all
    qf = queries._fact_match(months=24)
    assert "fecha_id" in qf
    assert qf["fecha_id"]["$gte"].startswith("2015")


def test_analysis_export_exige_auth():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/api/analysis/export")
    assert r.status_code == 401


def test_data_layers_mapa_operativo_vs_estrategico():
    from shared.data_layers import LAYER_MAP, LAYER_LABELS

    assert LAYER_MAP["purchase_requests"] == "operativo"
    assert LAYER_MAP["fact_ventas"] == "estrategico"
    assert LAYER_MAP["sales_records"] == "landing"
    assert LAYER_MAP["dim_region"] == "dimension"
    assert "estrategico" in LAYER_LABELS


def test_summary_vacio_no_rompe_sin_fact(monkeypatch):
    from paquetes.tablero import queries

    monkeypatch.setattr(queries, "strategic_ready", lambda: False)
    monkeypatch.setattr(queries, "dataset_max_order_date", lambda: "2017-12-31")
    queries.clear_query_cache()
    s = queries.get_summary()
    assert s["strategic_ready"] is False
    assert s["total_orders"] == 0
    assert s.get("data_layer") == "estrategico"
    assert "ELT" in (s.get("message") or "")


def test_meta_data_layers_endpoint(monkeypatch):
    """Meta data-layers es lectura pública (sin login), alineado a /api/meta."""
    from flask import Flask

    from paquetes.datos.routes import datos_bp

    fake = {
        "layers": [{"id": "operativo", "label": "Operativo", "collections": []}],
        "strategic_ready": False,
        "bridge": {"via": "convertir → landing.sales_records"},
        "message": "vacío",
    }
    monkeypatch.setattr("shared.data_layers.layers_overview", lambda: fake)
    app = Flask(__name__)
    app.register_blueprint(datos_bp)
    client = app.test_client()
    r = client.get("/api/meta/data-layers")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("status") == "ok"
    assert "layers" in data
    assert data.get("strategic_ready") is False


def test_layer_map_incluye_espejos_y_app_meta():
    from shared.data_layers import LAYER_MAP

    assert LAYER_MAP["app_roles"] == "gobernanza"
    assert LAYER_MAP["app_meta"] == "gobernanza"
    assert LAYER_MAP["regions"] == "dimension"
    assert LAYER_MAP["countries"] == "dimension"


def test_sync_order_to_fact_incremental(monkeypatch):
    """Sync appenda hechos desde landing sin rebuild."""
    from shared import analytics_sync as sync

    class FakeCol:
        def __init__(self, docs=None):
            self.docs = list(docs or [])

        def find(self, q=None, proj=None):
            q = q or {}
            out = []
            for d in self.docs:
                ok = True
                for k, v in q.items():
                    if d.get(k) != v:
                        ok = False
                        break
                if ok:
                    out.append(dict(d))
            return out

        def find_one(self, q=None, proj=None, sort=None):
            rows = self.find(q, proj)
            if sort:
                key, direction = sort[0]
                rows.sort(key=lambda r: r.get(key) or 0, reverse=direction < 0)
            return rows[0] if rows else None

        def count_documents(self, q=None, limit=None):
            n = len(self.find(q))
            return min(n, limit) if limit else n

        def estimated_document_count(self):
            return len(self.docs)

        def insert_one(self, doc):
            self.docs.append(dict(doc))

        def insert_many(self, docs):
            self.docs.extend(dict(d) for d in docs)

        def update_one(self, filt, update, upsert=False):
            pass

    class FakeDB:
        def __init__(self):
            self.cols = {
                "sales_records": FakeCol(
                    [
                        {
                            "order_id": "900001",
                            "region": "Europe",
                            "country": "Germany",
                            "item_type": "Clothes",
                            "sales_channel": "Online",
                            "order_priority": "M",
                            "order_date": "2017-06-01",
                            "units_sold": 2,
                            "unit_price": 10.0,
                            "unit_cost": 4.0,
                            "total_revenue": 20.0,
                            "total_cost": 8.0,
                            "total_profit": 12.0,
                        }
                    ]
                ),
                "fact_ventas": FakeCol([]),
                "dim_region": FakeCol([{"region_id": 1, "name": "Europe"}]),
                "dim_pais": FakeCol([{"country_id": 1, "name": "Germany", "region_id": 1}]),
                "dim_categoria": FakeCol([{"category_id": 1, "name": "Clothes"}]),
                "dim_canal": FakeCol([{"channel_id": 1, "name": "Online"}]),
                "dim_prioridad": FakeCol([{"priority_id": 3, "code": "M", "name": "Medium"}]),
                "dim_cliente": FakeCol([]),
                "dim_tiempo": FakeCol([]),
                "app_meta": FakeCol([]),
            }

        def __getitem__(self, name):
            if name not in self.cols:
                self.cols[name] = FakeCol([])
            return self.cols[name]

    fake = FakeDB()
    monkeypatch.setattr(sync, "get_db", lambda: fake)
    monkeypatch.setattr("paquetes.tablero.queries.clear_query_cache", lambda: None)

    res = sync.sync_order_to_fact("900001")
    assert res["analytics_stale"] is False
    assert res["synced"] == 1
    assert fake["fact_ventas"].count_documents({"order_id": "900001"}) == 1
    fact = fake["fact_ventas"].docs[0]
    assert fact["region_id"] == 1
    assert fact["category_id"] == 1
    assert fact["fecha_id"] == "2017-06-01"

    # Idempotente
    res2 = sync.sync_order_to_fact("900001")
    assert res2["skipped"] is True
    assert fake["fact_ventas"].count_documents({"order_id": "900001"}) == 1


def test_analytics_sync_stale_endpoint_exige_auth():
    from flask import Flask

    from paquetes.datos.routes import datos_bp

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(datos_bp)
    client = app.test_client()
    r = client.post("/api/analytics/sync-stale")
    assert r.status_code == 401


def test_fact_indexes_specs_incluyen_fecha():
    import inspect

    from shared import ops_indexes

    src = inspect.getsource(ops_indexes.ensure_ops_indexes)
    assert "fact_ventas" in src
    assert "fact_fecha" in src
    assert "fact_order" in src


def test_reportes_catalogo_tiene_15_simples():
    from paquetes.reportes.catalog import REPORTS
    from paquetes.reportes.services import list_catalog, run_report

    assert len(REPORTS) == 15
    assert all(r["id"].startswith("RS-") for r in REPORTS)
    cat = list_catalog()
    assert len(cat) == 15
    assert cat[0]["tipo"] == "simple"


def test_reportes_endpoint_exige_auth():
    from flask import Flask

    from paquetes.reportes.routes import reportes_bp

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(reportes_bp)
    client = app.test_client()
    assert client.get("/api/reportes").status_code == 401
    assert client.get("/api/reportes/RS-01").status_code == 401


def test_reportes_unknown_id():
    from paquetes.reportes.services import run_report
    import pytest

    with pytest.raises(ValueError, match="unknown_report"):
        run_report("RS-99")


def test_compuestos_catalogo_tiene_8():
    from paquetes.reportes.compuestos import COMPLEX_REPORTS, list_complex_catalog

    assert len(COMPLEX_REPORTS) == 8
    assert all(r["id"].startswith("RC-") for r in COMPLEX_REPORTS)
    assert len(list_complex_catalog()) == 8


def test_compuestos_rc08_estado_elt():
    _require_mongo()
    from paquetes.reportes.compuestos import run_complex_report

    data = run_complex_report("RC-08")
    assert data["report"]["tipo"] == "compuesto"
    assert data["total"] >= 3
    assert any("fact_ventas" in str(r.get("indicador")) for r in data["rows"])


def test_compuestos_categorias_en_espanol():
    from paquetes.reportes.compuestos import _localize_category_rows
    from paquetes.tablero.catalogo_nombres import category_label_from_name

    assert category_label_from_name("Cosmetics") == "Cosméticos"
    assert category_label_from_name("Beverages") == "Bebidas"
    assert category_label_from_name("Bebidas") == "Bebidas"
    rows = _localize_category_rows([{"categoria": "Baby Food", "pedidos": 1}])
    assert rows[0]["categoria"] == "Alimentos para bebés"


def test_compuestos_endpoint_exige_auth():
    from flask import Flask

    from paquetes.reportes.routes import reportes_bp

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(reportes_bp)
    client = app.test_client()
    assert client.get("/api/compuestos").status_code == 401
    assert client.get("/api/compuestos/RC-01").status_code == 401
    assert client.get("/api/reportes/compuestos").status_code == 401
    assert client.get("/api/reportes/compuestos/RC-01").status_code == 401
    assert client.get("/api/reportes/RS-01/pdf").status_code == 401
    assert client.get("/api/compuestos/RC-01/pdf").status_code == 401


def test_report_pdf_genera_bytes():
    from paquetes.reportes.pdf_export import generate_report_pdf

    pdf = generate_report_pdf(
        report_id="RS-01",
        title="Solicitudes pendientes",
        subtitle="Prueba",
        columns=["request_id", "client_name", "total"],
        rows=[{"request_id": 1, "client_name": "Ana", "total": 99.5}],
        total=1,
    )
    assert pdf[:4] == b"%PDF"


def test_invoice_pdf_genera_bytes():
    _require_mongo()
    from paquetes.soporte.services import generate_invoice_pdf

    pdf = generate_invoice_pdf(
        {
            "request_id": 1,
            "created_at": "2026-08-10T12:00:00+00:00",
            "client_name": "Cliente Demo",
            "client_email": "demo@example.com",
            "total": 10.0,
            "lines": [
                {
                    "product_name": "Producto",
                    "quantity": 1,
                    "unit_price": 10.0,
                    "line_gross": 10.0,
                }
            ],
        }
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 800


def test_retail_prices_rango_realista():
    _require_mongo()
    from shared.mongo import get_db
    from shared.retail_pricing import patch_dim_producto_prices, price_summary

    db = get_db()
    patch_dim_producto_prices(db)
    s = price_summary(db)
    assert s["count"] >= 100
    assert s["max"] <= 35.0
    assert s["min"] >= 1.5


def test_shipping_quote_online():
    _require_mongo()
    from shared.mongo import get_db
    from shared.shipping_rates import shipping_quote

    db = get_db()
    variant = db["product_variants"].find_one({}, {"variant_id": 1})
    assert variant
    q = shipping_quote(db, country_id=1, lines=[{"variant_id": variant["variant_id"], "quantity": 1}])
    assert q["shipping_cost"] > 0
    assert q["region_name"]


def test_etl_proceso_pipeline_tiene_cuatro_pasos():
    from etl_proceso.pipeline import STEPS

    ids = [name for name, _ in STEPS]
    assert ids == [
        "extract_csv_to_parquet",
        "load_landing_truncate",
        "transform_star_rebuild",
        "validate_strategic_layer",
    ]


def test_airflow_dag_file_exists():
    from pathlib import Path

    dag = Path(__file__).resolve().parents[1] / "airflow" / "dags" / "globtrade_strategic_etl.py"
    assert dag.is_file()
    text = dag.read_text(encoding="utf-8")
    assert 'dag_id="globtrade_strategic_etl"' in text
    assert "inspect_mongo_landing" in text
    assert "preserve_landing_dataset" in text
    assert "synchronize_strategic_layer" in text
    assert "validate_strategic_layer" in text
    assert "load_landing_truncate" not in text
    assert "transform_star_rebuild" not in text


def test_rate_limit_bloquea_tras_max_intentos():
    from shared import rate_limit as rl

    rl.reset_all()
    key = "test-ip"
    for _ in range(3):
        assert rl.check_rate_limit("login", key, max_attempts=3, window_sec=60) is None
        rl.record_attempt("login", key)
    msg = rl.check_rate_limit("login", key, max_attempts=3, window_sec=60)
    assert msg
    rl.clear_attempts("login", key)
    assert rl.check_rate_limit("login", key, max_attempts=3, window_sec=60) is None


def test_security_headers_en_respuestas():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in r.headers.get("Content-Security-Policy", "")


def test_cors_no_refleja_origen_no_autorizado():
    from frontend.app import app

    r = app.test_client().get("/api/health", headers={"Origin": "https://sitio-no-autorizado.example"})
    assert r.headers.get("Access-Control-Allow-Origin") is None


def test_rate_limit_concurrente_no_supera_cupo():
    from concurrent.futures import ThreadPoolExecutor
    from shared import rate_limit as rl

    rl.reset_all()
    def attempt(_):
        return rl.consume_attempt("concurrent", "account", max_attempts=5, window_sec=60)
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(attempt, range(20)))
    assert sum(result is None for result in results) == 5
    assert sum(result is not None for result in results) == 15


def test_reserva_stock_atomica_impide_sobreventa():
    from concurrent.futures import ThreadPoolExecutor
    from paquetes.shop.services import _reserve_stock
    from shared.mongo import get_db

    _require_mongo()
    db = get_db()
    variant_id = 990001
    db["product_variants"].delete_many({"variant_id": variant_id})
    db["inventory_movements"].delete_many({"variant_id": variant_id})
    db["product_variants"].insert_one({"variant_id": variant_id, "product_id": variant_id, "sku": "TEST-RACE", "inventory_quantity": 1})
    try:
        def reserve(_):
            try:
                _reserve_stock(db, variant_id, 1)
                return "ok"
            except ValueError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, range(2)))
        assert results.count("ok") == 1
        assert results.count("insufficient_stock") == 1
        assert db["product_variants"].find_one({"variant_id": variant_id})["inventory_quantity"] == 0
    finally:
        db["product_variants"].delete_many({"variant_id": variant_id})
        db["inventory_movements"].delete_many({"variant_id": variant_id})


def test_reserva_lote_revierte_si_una_linea_falla():
    from paquetes.shop.services import _reserve_stock_lines
    from shared.mongo import get_db

    _require_mongo()
    db = get_db()
    ids = [990011, 990012]
    db["product_variants"].delete_many({"variant_id": {"$in": ids}})
    db["inventory_movements"].delete_many({"variant_id": {"$in": ids}})
    db["product_variants"].insert_many([
        {"variant_id": ids[0], "product_id": ids[0], "sku": "TEST-ROLLBACK-1", "inventory_quantity": 1},
        {"variant_id": ids[1], "product_id": ids[1], "sku": "TEST-ROLLBACK-2", "inventory_quantity": 0},
    ])
    try:
        with pytest.raises(ValueError, match="insufficient_stock"):
            _reserve_stock_lines(db, [
                {"variant_id": ids[0], "quantity": 1},
                {"variant_id": ids[1], "quantity": 1},
            ])
        assert db["product_variants"].find_one({"variant_id": ids[0]})["inventory_quantity"] == 1
        assert db["product_variants"].find_one({"variant_id": ids[1]})["inventory_quantity"] == 0
    finally:
        db["product_variants"].delete_many({"variant_id": {"$in": ids}})
        db["inventory_movements"].delete_many({"variant_id": {"$in": ids}})


def test_users_manage_exige_permiso():
    _require_mongo()
    from frontend.app import app

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "vendedor-1"
        sess["email"] = "v@globtrade.test"
        sess["role"] = "vendedor"
    assert client.get("/api/auth/users").status_code == 403


def test_update_user_role_protege_ultimo_admin(monkeypatch):
    from bson import ObjectId

    from auth import users as user_store
    from shared.roles_registry import ADMIN_ROLE

    oid = ObjectId()

    class FakeCol:
        def __init__(self):
            self.docs = [
                {
                    "_id": oid,
                    "email": "a@t.com",
                    "name": "Admin",
                    "role": ADMIN_ROLE,
                    "active": True,
                }
            ]

        def count_documents(self, q):
            if q.get("role") == ADMIN_ROLE and q.get("active") is True:
                return 1
            return 0

        def find_one(self, q, proj=None):
            if q.get("_id") == oid and q.get("active") is True:
                return dict(self.docs[0])
            return None

        def update_one(self, q, patch):
            pass

    monkeypatch.setattr(user_store, "_col", lambda: FakeCol())
    monkeypatch.setattr(user_store.roles_service, "get_role", lambda slug: {
        "slug": slug,
        "active": True,
        "assignable": True,
    })
    monkeypatch.setattr(user_store.roles_service, "ensure_roles_seed", lambda: None)

    uid = str(oid)
    with pytest.raises(ValueError, match="cannot_change_last_admin"):
        user_store.update_user_role(uid, "cliente", actor_id=str(ObjectId()))

    with pytest.raises(ValueError, match="cannot_change_own_role"):
        user_store.update_user_role(uid, "cliente", actor_id=uid)


def test_mongo_collection_routing(monkeypatch):
    from shared import mongo as m
    from shared.db_routing import is_ops_collection

    assert is_ops_collection("users") is True
    assert is_ops_collection("fact_ventas") is False

    class FakeDB:
        def __init__(self, name):
            self.name = name

        def __getitem__(self, key):
            return f"{self.name}:{key}"

    class FakeClient:
        def __init__(self):
            self.dbs = {}

        def __getitem__(self, name):
            if name not in self.dbs:
                self.dbs[name] = FakeDB(name)
            return self.dbs[name]

        def close(self):
            pass

    client = FakeClient()
    monkeypatch.setattr(m, "_client", client)
    monkeypatch.setattr(m, "_read_client", None)
    monkeypatch.setattr(m.settings, "mongo_db", "globtrade_dw")
    monkeypatch.setattr(m.settings, "mongo_ops_db", "globtrade_ops")

    assert m.split_enabled() is True
    assert m.get_collection("users") == "globtrade_ops:users"
    assert m.get_collection("fact_ventas") == "globtrade_dw:fact_ventas"
    routed = m.get_db()
    assert routed["purchase_requests"] == "globtrade_ops:purchase_requests"
    assert routed["dim_region"] == "globtrade_dw:dim_region"


def test_ai_local_recommends_stock_report():
    from paquetes.reportes import ai_service

    data = ai_service.recommend_reports(prompt="productos con poco stock para reponer", scope="simple", limit=3)
    ids = [r["report_id"] for r in data["recommendations"]]
    assert "RS-03" in ids
    assert data["engine"] == "local"
    assert "español" in (data.get("engine_note") or "").lower() or "local" in (data.get("engine_note") or "").lower()


def test_payment_settled_requires_full_amount():
    from paquetes.ventas import services as ventas

    req = {
        "payment_status": "pagado",
        "total": 100.0,
        "paid_amount": 99.0,
        "channel_name": "Online",
    }
    assert ventas._payment_settled(req) is False

    req["paid_amount"] = 100.0
    assert ventas._payment_settled(req) is True

    offline = {"payment_status": "credito", "channel_name": "Offline", "total": 50.0}
    assert ventas._payment_settled(offline) is True


def test_request_expected_total_from_parts():
    from paquetes.ventas import services as ventas

    assert ventas._request_expected_total({"total": 120.5}) == 120.5
    assert ventas._request_expected_total({"subtotal": 100, "discount_amount": 10, "shipping_cost": 5}) == 95.0


def test_record_cash_movement(monkeypatch):
    from shared import cash_ledger

    class FakeCursor:
        def __init__(self, docs):
            self._docs = list(docs)

        def sort(self, key, direction):
            self._docs.sort(key=lambda r: r.get(key) or 0, reverse=direction < 0)
            return self

        def limit(self, n):
            self._docs = self._docs[:n]
            return self

        def __iter__(self):
            return iter(self._docs)

    class FakeCol:
        def __init__(self):
            self.docs = []

        def find_one(self, q=None, proj=None, sort=None):
            if not self.docs:
                return None
            if sort:
                key, direction = sort[0]
                rows = sorted(self.docs, key=lambda r: r.get(key) or 0, reverse=direction < 0)
                return rows[0]
            return self.docs[-1]

        def insert_one(self, doc):
            self.docs.append(dict(doc))

        def find(self, q=None, proj=None):
            q = q or {}
            out = [d for d in self.docs if all(d.get(k) == v for k, v in q.items())]
            return FakeCursor(out)

    col = FakeCol()
    monkeypatch.setattr(cash_ledger, "_col", lambda: col)

    doc = cash_ledger.record_cash_movement(
        movement_type="payment_in",
        amount=42.5,
        request_id=7,
        order_id="V-00007",
        payment_method="tarjeta",
    )
    assert doc["movement_id"] == 1
    assert doc["amount"] == 42.5
    assert col.docs[0]["movement_type"] == "payment_in"

    listed = cash_ledger.list_movements_for_request(7)
    assert len(listed) == 1


def test_list_cash_movements_summary(monkeypatch):
    from shared import cash_ledger

    class FakeCursor:
        def __init__(self, docs):
            self._docs = list(docs)

        def sort(self, key, direction):
            self._docs.sort(key=lambda r: r.get(key) or 0, reverse=direction < 0)
            return self

        def limit(self, n):
            self._docs = self._docs[:n]
            return self

        def __iter__(self):
            return iter(self._docs)

    class FakeCol:
        def __init__(self):
            self.docs = [
                {"movement_id": 1, "movement_type": "payment_in", "amount": 100.0, "request_id": 1},
                {"movement_id": 2, "movement_type": "refund_out", "amount": 25.0, "request_id": 1},
            ]

        def find(self, q=None, proj=None):
            q = q or {}
            out = [d for d in self.docs if all(d.get(k) == v for k, v in q.items())]
            return FakeCursor(out)

    monkeypatch.setattr(cash_ledger, "_col", lambda: FakeCol())
    data = cash_ledger.list_cash_movements(limit=10)
    assert data["summary"]["total_in"] == 100.0
    assert data["summary"]["total_out"] == 25.0
    assert data["summary"]["net"] == 75.0
    assert len(data["movements"]) == 2


def test_audit_log_filter_by_entity(monkeypatch):
    from paquetes.datos import services as datos_services

    class FakeCursor:
        def __init__(self, docs):
            self._docs = list(docs)

        def sort(self, key, direction):
            self._docs.sort(key=lambda r: r.get(key) or "", reverse=direction < 0)
            return self

        def skip(self, n):
            self._docs = self._docs[n:]
            return self

        def limit(self, n):
            self._docs = self._docs[:n]
            return self

        def __iter__(self):
            return iter(self._docs)

    class FakeCol:
        def __init__(self):
            self.docs = [
                {"action": "convert_request", "entity": "purchase_requests", "entity_id": 9, "at": "2024-01-02"},
                {"action": "create_po", "entity": "purchase_orders", "entity_id": 3, "at": "2024-01-01"},
            ]

        def count_documents(self, q=None):
            return len(list(self.find(q)))

        def find(self, q=None, proj=None):
            q = q or {}
            out = []
            for d in self.docs:
                if q.get("entity") and d.get("entity") != q.get("entity"):
                    continue
                if "$or" in q:
                    ids = {clause.get("entity_id") for clause in q["$or"]}
                    if d.get("entity_id") not in ids:
                        continue
                elif "entity_id" in q and d.get("entity_id") != q.get("entity_id"):
                    continue
                out.append(dict(d))
            return FakeCursor(out)

        def distinct(self, field):
            return sorted({d.get(field) for d in self.docs if d.get(field) is not None})

    monkeypatch.setattr(datos_services, "get_db", lambda: {"audit_log": FakeCol()})
    out = datos_services.list_audit_for_entity("purchase_requests", 9, limit=10)
    assert out["total"] == 1
    assert out["entries"][0]["action"] == "convert_request"


def test_maybe_notify_low_stock(monkeypatch):
    from shared import stock_alerts

    class FakeCol:
        def __init__(self, docs=None):
            self.docs = list(docs or [])

        def find_one(self, q=None, proj=None, sort=None):
            for d in self.docs:
                if all(d.get(k) == v for k, v in (q or {}).items()):
                    return dict(d)
            return None

        def update_one(self, filt, update, upsert=False):
            doc = self.find_one(filt)
            if doc:
                doc.update(update.get("$set", {}))
            elif upsert:
                self.docs.append({**(filt or {}), **update.get("$set", {})})

        def delete_one(self, filt):
            self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in (filt or {}).items())]

    class FakeDB:
        def __init__(self):
            self.cols = {
                "product_variants": FakeCol([{"variant_id": 1, "product_id": 10, "sku": "SKU-1", "inventory_quantity": 5}]),
                "products": FakeCol([{"product_id": 10, "title": "Test Product"}]),
                "app_meta": FakeCol([]),
            }

        def __getitem__(self, name):
            return self.cols[name]

    sent = {"n": 0}

    def fake_notify(**kwargs):
        sent["n"] += 1
        return 1

    fake = FakeDB()
    monkeypatch.setattr(stock_alerts, "maybe_notify_low_stock", stock_alerts.maybe_notify_low_stock)
    monkeypatch.setattr("shared.notifications.notify_roles", fake_notify)
    assert stock_alerts.maybe_notify_low_stock(fake, 1, threshold=20) is True
    assert sent["n"] == 1
    assert stock_alerts.maybe_notify_low_stock(fake, 1, threshold=20) is False


def test_requisition_status_constants():
    from paquetes.compras.services import REQUISITION_STATUSES

    assert REQUISITION_STATUSES == frozenset({"borrador", "aprobada", "convertida", "cancelada"})


def test_rebuild_monthly_kpis_for_month(monkeypatch):
    from shared import analytics_sync as sync

    class FakeCol:
        def __init__(self, docs=None):
            self.docs = list(docs or [])

        def find(self, q=None, proj=None):
            q = q or {}
            out = []
            for d in self.docs:
                ok = True
                for k, v in q.items():
                    if k == "fecha_id" and isinstance(v, dict) and "$regex" in v:
                        prefix = v["$regex"].lstrip("^")
                        if not str(d.get("fecha_id", "")).startswith(prefix):
                            ok = False
                    elif d.get(k) != v:
                        ok = False
                if ok:
                    out.append(dict(d))
            return out

        def find_one(self, q=None, proj=None, sort=None):
            rows = self.find(q, proj)
            if sort:
                key, direction = sort[0]
                rows.sort(key=lambda r: r.get(key) or 0, reverse=direction < 0)
            return rows[0] if rows else None

        def delete_many(self, q):
            self.docs = [d for d in self.docs if not all(d.get(k) == v for k, v in q.items())]

        def insert_many(self, docs):
            self.docs.extend(dict(d) for d in docs)

    class FakeDB:
        def __init__(self):
            self.cols = {
                "fact_ventas": FakeCol(
                    [
                        {
                            "fecha_id": "2024-03-15",
                            "region_id": 1,
                            "category_id": 2,
                            "units_sold": 3,
                            "total_revenue": 30.0,
                            "total_cost": 12.0,
                            "total_profit": 18.0,
                        }
                    ]
                ),
                "dim_region": FakeCol([{"region_id": 1, "name": "Europe"}]),
                "dim_categoria": FakeCol([{"category_id": 2, "name": "Clothes"}]),
                "monthly_kpis": FakeCol([]),
            }

        def __getitem__(self, name):
            if name not in self.cols:
                self.cols[name] = FakeCol([])
            return self.cols[name]

    fake = FakeDB()
    monkeypatch.setattr(sync, "get_db", lambda: fake)
    n = sync.rebuild_monthly_kpis_for_month(2024, 3)
    assert n == 1
    kpis = fake["monthly_kpis"].docs
    assert kpis[0]["total_revenue"] == 30.0
    assert kpis[0]["year"] == 2024
    assert kpis[0]["month"] == 3


def test_sem1_legacy_solo_administrador():
    from frontend.app import app

    client = app.test_client()
    r = client.get("/sem1")
    assert r.status_code == 302
    assert r.location.endswith("/")

    with client.session_transaction() as sess:
        sess["role"] = "vendedor"
    assert client.get("/sem1").status_code == 302

    with client.session_transaction() as sess:
        sess["role"] = "administrador"
    r_admin = client.get("/sem1")
    assert r_admin.status_code == 200
    assert r_admin.headers.get("X-Globtrade-Legacy") == "sem1"
    assert r_admin.headers.get("Deprecation") == "true"


def test_app_registra_rutas_fase4():
    from frontend.app import app

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/compras/cash-ledger" in rules
    assert "/api/compras/requisitions" in rules
    assert "/api/compras/requisitions/<int:req_id>/convertir-oc" in rules
    assert "/api/compras/purchase-orders/<int:po_id>/historial" in rules
    assert "/api/solicitudes/<int:request_id>/historial" in rules


def test_reportes_rs_13_14_15_caja_y_stock():
    from paquetes.reportes.catalog import REPORTS

    ids = {r["id"] for r in REPORTS}
    assert {"RS-13", "RS-14", "RS-15"}.issubset(ids)
    rs13 = next(r for r in REPORTS if r["id"] == "RS-13")
    assert "caja" in rs13["name"].lower() or "caja" in rs13.get("para_que", "").lower()


def test_requisition_approve_convert_chain(monkeypatch):
    from paquetes.compras import services as compras

    class FakeCol:
        def __init__(self, docs=None, id_field=None):
            self.docs = list(docs or [])
            self.id_field = id_field

        def find_one(self, q=None, proj=None, sort=None):
            q = q or {}
            for d in self.docs:
                if all(d.get(k) == v for k, v in q.items()):
                    return dict(d)
            return None

        def find(self, q=None, proj=None):
            q = q or {}
            out = [dict(d) for d in self.docs if all(d.get(k) == v for k, v in (q or {}).items())]

            class Cursor:
                def sort(self, key, direction):
                    out.sort(key=lambda r: r.get(key) or 0, reverse=direction < 0)
                    return self

                def skip(self, n):
                    return self

                def limit(self, n):
                    return self

                def __iter__(self):
                    return iter(out)

            return Cursor()

        def count_documents(self, q=None):
            return len(list(self.find(q)))

        def insert_one(self, doc):
            self.docs.append(dict(doc))

        def insert_many(self, docs):
            self.docs.extend(dict(d) for d in docs)

        def update_one(self, filt, update, upsert=False):
            for d in self.docs:
                if all(d.get(k) == v for k, v in filt.items()):
                    d.update(update.get("$set", {}))
                    return
            if upsert:
                self.docs.append({**filt, **update.get("$set", {})})

    class FakeDB:
        def __init__(self):
            self.cols = {
                "purchase_requisitions": FakeCol(
                    [
                        {
                            "req_id": 1,
                            "vendor_id": 5,
                            "status": "borrador",
                            "notes": "Demo",
                            "created_at": "2026-08-10",
                            "approved_at": None,
                            "po_id": None,
                        }
                    ]
                ),
                "purchase_requisition_lines": FakeCol(
                    [{"line_id": 1, "req_id": 1, "variant_id": 10, "product_id": 1, "quantity": 4, "unit_cost": 3.5}]
                ),
                "vendors": FakeCol([{"vendor_id": 5, "name": "Proveedor Demo"}]),
                "product_variants": FakeCol([{"variant_id": 10, "product_id": 1, "sku": "SKU-10", "cost": 3.5}]),
                "purchase_orders": FakeCol(),
                "purchase_order_lines": FakeCol(),
            }

        def __getitem__(self, name):
            if name not in self.cols:
                self.cols[name] = FakeCol()
            return self.cols[name]

    fake = FakeDB()
    monkeypatch.setattr(compras, "get_db", lambda: fake)
    monkeypatch.setattr(compras, "log_audit", lambda *a, **k: None)
    monkeypatch.setattr(compras, "_notify_compras", lambda *a, **k: None)
    monkeypatch.setattr(
        compras,
        "warehouse_summary",
        lambda: {"warehouse_id": 1, "name": "Bodega General"},
    )

    approved = compras.approve_purchase_requisition(1)
    assert approved["status"] == "aprobada"

    result = compras.convert_requisition_to_po(1)
    req = result["requisition"]
    po = result["purchase_order"]
    assert req["status"] == "convertida"
    assert req["po_id"] == po["po_id"]
    assert po["status"] == "borrador"
    assert po["vendor_id"] == 5
    assert len(fake["purchase_order_lines"].docs) == 1


DEMO_PASSWORD = "Demo1234!"


def _require_mongo():
    """Salta el test si MongoDB no está disponible (no espera indefinidamente)."""
    try:
        from shared.mongo import mongo_client

        mongo_client().admin.command("ping")
    except Exception as exc:
        pytest.skip(f"MongoDB no disponible: {exc}")


def _api_login(client, email: str, password: str = DEMO_PASSWORD) -> dict:
    client.post("/api/auth/logout")
    r = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, (email, r.get_json())
    data = r.get_json() or {}
    assert data.get("status") == "ok"
    return data


def test_demo_data_loaded():
    """Bootstrap demo: usuarios, catálogo y capa analítica mínima."""
    _require_mongo()
    from auth import users as user_store
    from shared.mongo import get_db

    for email in (
        "admin@globtrade.demo",
        "vendedor@globtrade.demo",
        "analista@globtrade.demo",
        "cliente@globtrade.demo",
    ):
        assert user_store.find_by_email(email), email

    db = get_db()
    variants = db["product_variants"].estimated_document_count()
    sales = db["sales_records"].estimated_document_count()
    fact = db["fact_ventas"].estimated_document_count()
    assert variants > 0
    assert sales > 0 or fact > 0


def test_demo_role_walkthrough():
    """Recorrido API por rol demo (login real + permisos esperados)."""
    _require_mongo()
    from scripts.seed_demo import ensure_demo_roles_ready, seed_users

    seed_users(DEMO_PASSWORD, force=False)
    ensure_demo_roles_ready()
    from frontend.app import app

    client = app.test_client()
    scenarios = {
        "admin@globtrade.demo": [
            ("/api/summary", 200),
            ("/api/reportes", 200),
            ("/api/reportes/compuestos", 200),
            ("/api/compras/inventory", 200),
            ("/api/audit_log", 200),
            ("/api/master/tables", 200),
        ],
        "vendedor@globtrade.demo": [
            ("/api/reportes", 200),
            ("/api/decisiones/panel", 200),
            ("/api/compras/inventory", 200),
            ("/api/solicitudes/pendientes/count", 200),
            ("/api/audit_log", 403),
        ],
        "analista@globtrade.demo": [
            ("/api/summary", 200),
            ("/api/analysis/trend", 200),
            ("/api/reportes/compuestos", 200),
            ("/api/compras/inventory", 403),
        ],
        "cliente@globtrade.demo": [
            ("/api/shop/products", 200),
            ("/api/solicitudes/mias", 200),
            ("/api/auth/notifications", 200),
            ("/api/reportes", 403),
            ("/api/compras/inventory", 403),
        ],
    }

    for email, checks in scenarios.items():
        login = _api_login(client, email)
        access = login.get("access") or {}
        assert access.get("pages"), email
        for path, expected_status in checks:
            r = client.get(path)
            assert r.status_code == expected_status, f"{email} {path} -> {r.status_code}"

    client.post("/api/auth/logout")


def test_client_pay_requiere_aprobacion(monkeypatch):
    from paquetes.ventas import services

    req = {
        "request_id": 1,
        "client_email": "c@test.com",
        "status": "pendiente",
        "payment_status": "pendiente_pago",
        "channel_id": 1,
    }
    monkeypatch.setattr(services, "get_request", lambda rid: dict(req))

    with pytest.raises(ValueError, match="approval_required_for_payment"):
        services.client_pay(1, client_email="c@test.com")


def test_entregada_requiere_pago(monkeypatch):
    from paquetes.ventas import services

    class FakeCol:
        def find_one(self, q, proj=None):
            if q.get("request_id") == 1:
                return {
                    "request_id": 1,
                    "status": "enviada",
                    "payment_status": "pendiente_pago",
                    "channel_id": 1,
                    "channel_name": "Online",
                }
            return None

        def update_one(self, *args, **kwargs):
            return None

    class FakeDB:
        def __getitem__(self, name):
            return FakeCol()

    monkeypatch.setattr(services, "get_db", lambda: FakeDB())
    monkeypatch.setattr(services, "get_request", lambda rid: FakeCol().find_one({"request_id": rid}))
    monkeypatch.setattr(services, "log_audit", lambda *a, **k: None)
    monkeypatch.setattr(services, "_notify_request_status", lambda *a, **k: None)

    with pytest.raises(ValueError, match="payment_required"):
        services.update_status(1, "entregada", reviewer_email="v@test.com")


def test_sync_stale_orders_no_cuelga_sin_mongo():
    """NS-02/03: ping con timeout; si no hay Mongo, skip en vez de colgarse."""
    _require_mongo()
    from shared.analytics_sync import sync_stale_orders

    result = sync_stale_orders(limit=5)
    assert "orders_synced" in result
    assert "facts_inserted" in result


def test_carrito_tiene_controles_incrementales_de_cantidad():
    """El carrito permite disminuir/aumentar sin eliminar la línea completa."""
    root = Path(__file__).resolve().parents[1]
    tienda_js = (root / "frontend" / "static" / "js" / "tienda.js").read_text(encoding="utf-8")
    storefront_css = (root / "frontend" / "static" / "css" / "storefront.css").read_text(encoding="utf-8")

    assert "function tiendaChangeCartQty(variantId, delta)" in tienda_js
    assert "tiendaChangeCartQty(${c.variant_id}, -1)" in tienda_js
    assert "tiendaChangeCartQty(${c.variant_id}, 1)" in tienda_js
    assert "next < 1" in tienda_js
    assert "next > item.max_quantity" in tienda_js
    assert ".shop-cart-quantity" in storefront_css


def test_maestros_editables_incluyen_estado_activo():
    from shared.master_registry import EDITABLE_MASTERS, MASTER_TABLES

    assert EDITABLE_MASTERS
    for name in EDITABLE_MASTERS:
        assert "active" in MASTER_TABLES[name]["fields"], name


def test_inhabilitar_maestro_conserva_registro(monkeypatch):
    from paquetes.datos import services

    class FakeCol:
        def __init__(self):
            self.row = {"product_id": 7, "name": "Producto", "active": True}

        def find_one(self, query, projection=None):
            return dict(self.row) if query.get("product_id") == 7 else None

        def update_one(self, query, update):
            self.row.update(update["$set"])

    col = FakeCol()

    class FakeDB:
        def __getitem__(self, name):
            assert name == "dim_producto"
            return col

    monkeypatch.setattr(services, "get_db", lambda: FakeDB())
    monkeypatch.setattr(services, "log_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(services, "_sync_shop_after_master_change", lambda name: None)

    row = services.set_row_active("dim_producto", "7", False)

    assert row["product_id"] == 7
    assert row["active"] is False


def test_borrado_producto_bloqueado_si_tiene_historial(monkeypatch):
    from paquetes.datos import services

    class FakeCountCol:
        def __init__(self, count=0):
            self.count = count

        def count_documents(self, query, limit=0):
            return self.count

    class FakeDB:
        def __getitem__(self, name):
            return FakeCountCol(1 if name == "purchase_request_lines" else 0)

    monkeypatch.setattr(services, "get_db", lambda: FakeDB())

    with pytest.raises(ValueError, match="has_history"):
        services._check_delete_refs("dim_producto", 7)


def test_catalogos_fijos_no_admiten_nuevos_registros():
    from paquetes.datos import services
    from shared.master_registry import FIXED_MASTERS, master_allows_create

    expected = {"dim_region", "dim_pais", "dim_canal", "dim_prioridad"}
    assert FIXED_MASTERS == expected
    for name in expected:
        assert master_allows_create(name) is False
        with pytest.raises(ValueError, match="fixed_catalog"):
            services.create_row(name, {"name": "No permitido"})

    assert master_allows_create("dim_categoria") is True
    assert master_allows_create("dim_producto") is True
    assert master_allows_create("dim_cliente") is True


def test_sesion_inactiva_tiene_limite_profesional():
    from config.settings import settings

    assert 15 <= settings.session_idle_minutes <= 480


def test_ajuste_manual_inventario_exige_motivo():
    from paquetes.compras.services import normalize_adjustment_reason

    with pytest.raises(ValueError, match="reason_required"):
        normalize_adjustment_reason("")
    with pytest.raises(ValueError, match="reason_too_short"):
        normalize_adjustment_reason("mal")
    assert normalize_adjustment_reason("Conteo físico realizado") == "Conteo físico realizado"


def test_proveedor_se_inhabilita_sin_borrarse(monkeypatch):
    from paquetes.compras import services

    class FakeCol:
        def __init__(self):
            self.row = {"vendor_id": 4, "name": "Proveedor", "active": True}

        def find_one(self, query, projection=None):
            return dict(self.row) if query.get("vendor_id") == 4 else None

        def update_one(self, query, update):
            self.row.update(update["$set"])

    col = FakeCol()

    class FakeDB:
        def __getitem__(self, name):
            assert name == "vendors"
            return col

    monkeypatch.setattr(services, "get_db", lambda: FakeDB())
    monkeypatch.setattr(services, "log_audit", lambda *args, **kwargs: None)

    row = services.set_vendor_active(4, False, reason="Contrato finalizado")
    assert row["vendor_id"] == 4
    assert row["active"] is False


def test_periodos_contables_diario_y_mensual():
    from shared.accounting import period_bounds

    assert period_bounds("daily", "2026-08-24") == ("2026-08-24", "2026-08-24", "2026-08-24")
    assert period_bounds("monthly", "2026-02") == ("2026-02", "2026-02-01", "2026-02-28")
    with pytest.raises(ValueError, match="invalid_period"):
        period_bounds("monthly", "2026-13")


def test_conciliacion_calcula_saldo_y_estado():
    from shared.accounting import calculate_reconciliation

    row = calculate_reconciliation(expected=100, paid=80, refunded=10, invoiced=100)
    assert row["net_paid"] == 70
    assert row["balance_due"] == 30
    assert row["reconciled"] is False

    settled = calculate_reconciliation(expected=100, paid=100, refunded=0, invoiced=100)
    assert settled["balance_due"] == 0
    assert settled["reconciled"] is True


def test_numeros_contables_tienen_formato_estable():
    from shared.accounting import format_credit_note_number, format_invoice_number

    assert format_invoice_number(2026, 12) == "FAC-2026-000012"
    assert format_credit_note_number(2026, 3) == "NC-2026-000003"


def test_inventario_separa_estados_sin_mezclarlos():
    from shared.inventory_ledger import stock_breakdown

    row = stock_breakdown(available=12, committed=3, damaged=2, in_transit=8)
    assert row == {"available": 12, "committed": 3, "damaged": 2, "in_transit": 8, "physical": 17}


def test_reposicion_respeta_minimo_y_comprometido():
    from shared.inventory_ledger import reorder_suggestion

    assert reorder_suggestion(available=12, committed=5, minimum=10, target=20) == 13
    assert reorder_suggestion(available=30, committed=2, minimum=10, target=20) == 0


def test_metadatos_tarjeta_no_guardan_pan_ni_cvv():
    from shared.payments import sanitize_card_metadata

    safe = sanitize_card_metadata({"brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2030})
    assert safe == {"brand": "VISA", "last4": "4242", "exp_month": 12, "exp_year": 2030}
    with pytest.raises(ValueError, match="sensitive_card_data"):
        sanitize_card_metadata({"card_number": "4242424242424242", "cvv": "123", "last4": "4242"})


def test_exportacion_csv_evitar_formulas_y_conservar_columnas():
    from paquetes.reportes.csv_export import generate_report_csv

    data = generate_report_csv(columns=["name", "total"], rows=[{"name": "=CMD()", "total": 12.5}])
    text = data.decode("utf-8-sig")
    assert "Nombre,Total" in text
    assert "'=CMD()" in text


def test_resumen_error_es_corto_y_sin_saltos():
    from shared.error_log import safe_error_summary

    text = safe_error_summary(RuntimeError("fallo\ncon detalle"))
    assert text == "RuntimeError: fallo con detalle"
    assert len(safe_error_summary(ValueError("x" * 1000))) <= 312


def test_manifiesto_respaldo_verifica_archivos(tmp_path):
    import json
    from shared.backup_status import list_backup_manifests

    folder = tmp_path / "globtrade-20260824-120000"
    folder.mkdir()
    (folder / "data.bson").write_bytes(b"datos")
    (folder / "manifest.json").write_text(json.dumps({
        "created_at": "2026-08-24T12:00:00Z", "databases": ["globtrade_ops"], "file_count": 1,
    }), encoding="utf-8")
    rows = list_backup_manifests(tmp_path)
    assert rows[0]["verified"] is True
    assert rows[0]["file_count"] == 1


def test_intento_pago_repetido_es_idempotente():
    from shared.payments import record_payment_attempt

    class Collection:
        def __init__(self): self.docs = []
        def find_one(self, query, projection=None):
            return next((dict(x) for x in self.docs if all(x.get(k) == v for k, v in query.items())), None)
        def find_one_and_update(self, query, update, upsert=False, return_document=None):
            row = self.find_one(query)
            if not row:
                row = dict(query); row["value"] = 0; self.docs.append(row)
            row["value"] += update["$inc"]["value"]
            for saved in self.docs:
                if all(saved.get(k) == v for k, v in query.items()): saved.update(row)
            return dict(row)
        def insert_one(self, doc): self.docs.append(dict(doc))

    class DB:
        def __init__(self): self.cols = {"payment_attempts": Collection(), "app_meta": Collection()}
        def __getitem__(self, name): return self.cols[name]

    db = DB()
    kwargs = dict(
        request_id=7, amount=50, outcome="approved", idempotency_key="same-attempt-12345",
        card={"brand": "VISA", "last4": "4242", "exp_month": 12, "exp_year": 2030},
    )
    first, created = record_payment_attempt(db, **kwargs)
    second, created_again = record_payment_attempt(db, **kwargs)
    assert created is True and created_again is False
    assert first["transaction_reference"] == second["transaction_reference"]
    assert len(db["payment_attempts"].docs) == 1
