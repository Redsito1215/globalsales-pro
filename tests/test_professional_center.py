from pathlib import Path

from paquetes.profesional import services


def _client_with_session():
    from frontend.app import app

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = "test-user"
        session["email"] = "gerencia@altavia.test"
        session["role"] = "administrador"
    return client


def test_professional_routes_require_session():
    from frontend.app import app

    response = app.test_client().get("/api/profesional/resumen")
    assert response.status_code == 401


def test_professional_summary_contract(monkeypatch):
    monkeypatch.setattr(services, "professional_home", lambda role: {
        "role": role, "kpis": [{"label": "Pedidos", "value": 4, "format": "number"}],
        "pending_approvals": 1, "quick_actions": [{"label": "Alertas", "phase": 2}],
    })
    response = _client_with_session().get("/api/profesional/resumen")
    assert response.status_code == 200
    assert response.get_json()["role"] == "administrador"
    assert response.get_json()["quick_actions"][0]["phase"] == 2


def test_profile_not_found_is_clear(monkeypatch):
    monkeypatch.setattr(services, "product_profile", lambda product_id: None)
    response = _client_with_session().get("/api/profesional/productos/999999")
    assert response.status_code == 404
    assert "no encontrado" in response.get_json()["message"].lower()


def test_short_global_search_is_rejected():
    try:
        services.global_search("a")
    except ValueError as exc:
        assert str(exc) == "query_too_short"
    else:
        raise AssertionError("La búsqueda de un carácter debía rechazarse")


def test_professional_ui_has_exactly_eleven_phases():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/static/js/profesional.js").read_text(encoding="utf-8")
    assert "const professionalPhases" in script
    assert script.count("['") >= 11
    assert "Fase ${n} de 11" in script
    assert "seguridad empresarial" not in script.lower()


def test_advanced_operations_contract(monkeypatch):
    monkeypatch.setattr(services, "logistics_overview", lambda: {"summary": {"in_transit": 2}, "shipments": []})
    monkeypatch.setattr(services, "demand_forecast", lambda: [{"product_id": 1, "suggested_reorder": 8}])
    monkeypatch.setattr(services, "profitability_summary", lambda: {"adjusted_profit": 120.0})
    monkeypatch.setattr(services, "loyalty_overview", lambda: {"summary": {"vip": 1}, "customers": []})
    monkeypatch.setattr(services, "analytics_freshness", lambda: {"clickhouse_status": "ok"})
    monkeypatch.setattr(services, "profitability_comparison", lambda: {"products": [], "categories": [], "clients": [], "regions": []})
    response = _client_with_session().get("/api/profesional/operacion-avanzada")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["logistics"]["summary"]["in_transit"] == 2
    assert payload["forecast"][0]["suggested_reorder"] == 8
    assert payload["profitability"]["adjusted_profit"] == 120.0
    assert payload["loyalty"]["summary"]["vip"] == 1


def test_quality_contract_includes_business_rules(monkeypatch):
    monkeypatch.setattr(services, "data_quality", lambda: [])
    monkeypatch.setattr(services, "quality_issues", lambda: {"total": 3, "issues": [{"rule": "Stock negativo", "count": 3}]})
    response = _client_with_session().get("/api/profesional/calidad")
    assert response.status_code == 200
    assert response.get_json()["validation"]["total"] == 3


def test_strategic_etl_is_scheduled_daily():
    root = Path(__file__).resolve().parents[1]
    dag = (root / "airflow/dags/globtrade_strategic_etl.py").read_text(encoding="utf-8")
    assert 'schedule="0 2 * * *"' in dag


def test_professional_mobile_and_advanced_ui_are_present():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/static/js/profesional.js").read_text(encoding="utf-8")
    css = (root / "frontend/static/css/profesional.css").read_text(encoding="utf-8")
    assert "/operacion-avanzada" in script
    assert "Pronóstico y reposición sugerida" in script
    assert "Clientes para fidelización" in script
    assert "scroll-snap-type" in css


def test_forecast_can_create_purchase_requisition(monkeypatch):
    monkeypatch.setattr(services, "create_forecast_requisition", lambda product_id, quantity: {
        "req_id": 41, "status": "borrador", "lines": [{"product_id": product_id, "quantity": quantity}]
    })
    response = _client_with_session().post("/api/profesional/pronostico/requisicion", json={"product_id": 2, "quantity": 18})
    assert response.status_code == 201
    assert response.get_json()["requisition"]["req_id"] == 41


def test_loyalty_campaign_contract(monkeypatch):
    monkeypatch.setattr(services, "create_loyalty_campaign", lambda segment, actor: {"code": "ALTAVIA-VIP", "segment": segment})
    response = _client_with_session().post("/api/profesional/fidelizacion/campana", json={"segment": "vip"})
    assert response.status_code == 201
    assert response.get_json()["campaign"]["code"] == "ALTAVIA-VIP"


def test_advanced_ui_connects_actions_chart_and_export():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/static/js/profesional.js").read_text(encoding="utf-8")
    for expected in ("proDrawForecast", "proCreateForecastReq", "proCreateCampaign", "proExportAdvanced", "Comparación de rentabilidad"):
        assert expected in script


def test_clickhouse_monitor_contract(monkeypatch):
    monkeypatch.setattr(services, "clickhouse_monitor", lambda: {
        "online": True, "status": "operativo", "tables": [{"table": "fact_sales", "records": 12}],
        "last_run": {"status": "success"}, "airflow_url": "http://localhost:8080",
    })
    response = _client_with_session().get("/api/profesional/clickhouse")
    assert response.status_code == 200
    assert response.get_json()["tables"][0]["records"] == 12


def test_professional_ui_includes_lots_prices_and_clickhouse():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/static/js/profesional.js").read_text(encoding="utf-8")
    for expected in ("Lotes, caducidad y trazabilidad", "Listas de precios por cliente o canal", "proLoadClickHouse"):
        assert expected in script


def test_seller_goal_and_usability_routes(monkeypatch):
    from shared import sales_performance
    monkeypatch.setattr(sales_performance, "save_goal", lambda data, actor: {"goal_id": 9, **data})
    monkeypatch.setattr(sales_performance, "save_usability_feedback", lambda data, actor: {"score": data["score"], "actor": actor})
    client = _client_with_session()
    goal = client.post("/api/profesional/vendedores", json={"seller_email": "v@a.test", "target": 100})
    feedback = client.post("/api/profesional/usabilidad/opinion", json={"score": 4})
    assert goal.status_code == 201 and goal.get_json()["goal"]["goal_id"] == 9
    assert feedback.status_code == 201 and feedback.get_json()["feedback"]["score"] == 4


def test_professional_ui_has_bulk_prices_commissions_and_guided_test():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/static/js/profesional.js").read_text(encoding="utf-8")
    for expected in ("Productos y precios separados por coma", "Metas y comisiones de vendedores", "Prueba guiada de facilidad de uso"):
        assert expected in script
