from datetime import date, timedelta

from paquetes.decisiones import services


def test_product_portfolio_recommends_reorder_and_flags_stagnant(monkeypatch):
    monkeypatch.setattr(services, "ping_clickhouse", lambda: True)
    recent = date.today() - timedelta(days=2)

    def fake_query(sql, parameters=None):
        if "FROM fact_sales" in sql:
            return [
                {"product_id": 1, "product": "Producto líder", "category": "A", "orders": 20, "units": 90,
                 "revenue": 9000, "cost": 5400, "profit": 3600, "margin_pct": 40, "last_sale": recent, "avg_daily_units": 1},
            ]
        return [
            {"product_id": 1, "product": "Producto líder", "category": "A", "stock": 5, "inventory_value": 250},
            {"product_id": 2, "product": "Producto detenido", "category": "B", "stock": 20, "inventory_value": 1000},
        ]

    monkeypatch.setattr(services, "query_rows", fake_query)
    result = services.product_portfolio(lookback_days=90)

    assert result["ready"] is True
    assert result["summary"]["reorder_products"] == 1
    assert result["summary"]["stagnant_products"] == 1
    assert result["summary"]["capital_at_risk"] == 1000
    leader = next(row for row in result["items"] if row["product_id"] == 1)
    assert leader["quadrant"] == "Estrella"
    assert leader["reorder_qty"] == 16


def test_product_portfolio_explains_missing_clickhouse(monkeypatch):
    monkeypatch.setattr(services, "ping_clickhouse", lambda: False)
    result = services.product_portfolio()
    assert result["ready"] is False
    assert "ClickHouse" in result["message"]


def test_forecast_values_detects_growth_and_reports_confidence():
    result = services._forecast_values([10, 12, 14, 16, 18, 20], periods=3)

    assert len(result["forecast"]) == 3
    assert result["forecast"][2] > result["forecast"][0]
    assert result["trend_pct"] > 0
    assert result["confidence"] in {"alta", "media", "baja"}


def test_demand_forecast_combines_prediction_with_inventory(monkeypatch):
    monkeypatch.setattr(services, "ping_clickhouse", lambda: True)

    def fake_query(sql, parameters=None):
        if "inventory_snapshot" in sql:
            return [{"product_id": 1, "stock": 5}]
        return [
            {"product_id": 1, "product": "Mangos", "category": "Frutas", "month": f"2025-0{month}-01", "units": units}
            for month, units in enumerate([10, 12, 14, 16, 18, 20], start=1)
        ]

    monkeypatch.setattr(services, "query_rows", fake_query)
    result = services.demand_forecast(months=6, horizon=3)

    assert result["ready"] is True
    assert result["items"][0]["recommended_purchase"] > 0
    assert result["items"][0]["forecast_total"] > 0


def test_demand_forecast_explains_missing_clickhouse(monkeypatch):
    monkeypatch.setattr(services, "ping_clickhouse", lambda: False)
    result = services.demand_forecast()
    assert result["ready"] is False
    assert "ClickHouse" in result["message"]
