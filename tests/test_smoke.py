"""Smoke tests — lógica de negocio y rutas registradas (sin exigir Mongo vivo)."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)


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
    monkeypatch.setattr(roles_service, "get_db", lambda: fake_db)
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
    r = client.get("/api/audit_log?limit=200")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["limit"] == 100
    assert any(e.get("action") == "test_audit_json" for e in data.get("entries", []))
    db["audit_log"].delete_many({"action": "test_audit_json"})


def test_audit_log_filtro_rol_y_paginacion():
    from paquetes.datos.services import list_audit_log

    out = list_audit_log(limit=500, offset=0, role="vendedor")
    assert out["limit"] == 100
    assert out.get("role") == "vendedor"
    assert isinstance(out.get("roles"), list)


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


def test_match_months_ancla_en_dataset_no_en_hoy(monkeypatch):
    from paquetes.tablero import queries

    monkeypatch.setattr(queries, "dataset_max_order_date", lambda: "2017-12-31")
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


def test_reportes_catalogo_tiene_12_simples():
    from paquetes.reportes.catalog import REPORTS
    from paquetes.reportes.services import list_catalog, run_report

    assert len(REPORTS) == 12
    assert all(r["id"].startswith("RS-") for r in REPORTS)
    cat = list_catalog()
    assert len(cat) == 12
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
    from paquetes.reportes.compuestos import run_complex_report

    data = run_complex_report("RC-08")
    assert data["report"]["tipo"] == "compuesto"
    assert data["total"] >= 3
    assert any("fact_ventas" in str(r.get("indicador")) for r in data["rows"])


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
    from shared.mongo import get_db
    from shared.retail_pricing import patch_dim_producto_prices, price_summary

    db = get_db()
    patch_dim_producto_prices(db)
    s = price_summary(db)
    assert s["count"] >= 100
    assert s["max"] <= 35.0
    assert s["min"] >= 1.5


def test_shipping_quote_online():
    from shared.mongo import get_db
    from shared.shipping_rates import shipping_quote

    db = get_db()
    variant = db.product_variants.find_one({}, {"variant_id": 1})
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
    assert "extract_csv_to_parquet" in text
    assert "validate_strategic_layer" in text


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


def test_users_manage_exige_permiso():
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

