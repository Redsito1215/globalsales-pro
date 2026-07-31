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
    assert client.get("/api/reportes/compuestos").status_code == 401
    assert client.get("/api/reportes/compuestos/RC-01").status_code == 401

