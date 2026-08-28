from paquetes.datos import services


def test_master_product_filters_reach_service(monkeypatch):
    from frontend.app import app

    captured = {}

    def fake_list_rows(name, **kwargs):
        captured["name"] = name
        captured.update(kwargs)
        return {"name": name, "rows": [], "total": 0, "filter_options": {"categories": [], "vendors": []}}

    monkeypatch.setattr(services, "list_rows", fake_list_rows)
    response = app.test_client().get(
        "/api/master/dim_producto?category_id=6&vendor_id=2&active=true&search=manzana"
    )
    assert response.status_code == 200
    assert captured["name"] == "dim_producto"
    assert captured["category_id"] == 6
    assert captured["vendor_id"] == 2
    assert captured["active"] is True
    assert captured["search"] == "manzana"


def test_master_product_filters_reject_invalid_ids():
    from frontend.app import app

    response = app.test_client().get("/api/master/dim_producto?vendor_id=no-valido")
    assert response.status_code == 400
    assert "filtros" in response.get_json()["message"].lower()
