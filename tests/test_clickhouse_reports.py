from datetime import date

from paquetes.reportes import compuestos
from etl_proceso.steps.sync_clickhouse import _date, _number


def test_complex_catalog_declares_clickhouse_and_charts():
    catalog = compuestos.list_complex_catalog()
    assert len(catalog) == 8
    assert all(row["data_layer"] == "clickhouse" for row in catalog)
    assert all(row.get("chart", {}).get("type") for row in catalog)


def test_report_returns_actionable_message_when_clickhouse_is_down(monkeypatch):
    monkeypatch.setattr(compuestos, "ping_clickhouse", lambda: False)
    result = compuestos.run_complex_report("RC-01")
    assert result["rows"] == []
    assert "ClickHouse" in result["message"]


def test_sales_report_passes_safe_filters_to_clickhouse(monkeypatch):
    captured = {}
    monkeypatch.setattr(compuestos, "ping_clickhouse", lambda: True)

    def fake_query(sql, parameters=None):
        captured["sql"] = sql
        captured["parameters"] = parameters
        return [{"mes": "2026-08", "categoria": "Tecnología", "ingresos": 10}]

    monkeypatch.setattr(compuestos, "query_rows", fake_query)
    result = compuestos.run_complex_report(
        "RC-01", filters={"start": "2026-08-01", "category": "Tecnología"}
    )
    assert result["total"] == 1
    assert captured["parameters"]["start"] == date(2026, 8, 1)
    assert captured["parameters"]["category"] == "Tecnología"
    assert "{category:String}" in captured["sql"]


def test_clickhouse_sync_value_normalization():
    assert _date("2026-08-25T12:00:00") == date(2026, 8, 25)
    assert _number("12.5") == 12.5
    assert _number(None) == 0
