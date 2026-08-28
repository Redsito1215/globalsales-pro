"""Cliente y esquema de la capa analítica ClickHouse de GLOBTRADE."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from config.settings import settings


@lru_cache(maxsize=1)
def get_clickhouse_client(*, database: str | None = None):
    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=database or settings.clickhouse_database,
        secure=settings.clickhouse_secure,
        connect_timeout=5,
        send_receive_timeout=30,
    )


def ensure_database_and_schema() -> None:
    root = get_clickhouse_client(database="default")
    db = settings.clickhouse_database.replace("`", "")
    root.command(f"CREATE DATABASE IF NOT EXISTS `{db}`")
    client = get_clickhouse_client()
    statements = [
        """
        CREATE TABLE IF NOT EXISTS fact_sales (
          sale_id UInt64, order_id String, sale_date Date,
          product_id UInt64, product String, category_id UInt32, category String,
          vendor_id UInt32, vendor String,
          region String, country String, channel String,
          units Float64, unit_price Float64, unit_cost Float64,
          revenue Float64, cost Float64, profit Float64,
          coupon String, discount Float64
        ) ENGINE = MergeTree ORDER BY (sale_date, category_id, product_id, order_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_purchases (
          purchase_id String, purchase_date Date, status LowCardinality(String),
          vendor String, amount Float64
        ) ENGINE = MergeTree ORDER BY (purchase_date, status, purchase_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS inventory_snapshot (
          snapshot_at DateTime, product_id UInt64, product String,
          category_id UInt32, category String, stock Float64, inventory_value Float64
        ) ENGINE = ReplacingMergeTree(snapshot_at) ORDER BY (product_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_logistics (
          request_id String, created_date Date, shipped_date Nullable(Date),
          region String, country String, days_to_ship Nullable(Int32), status String
        ) ENGINE = MergeTree ORDER BY (created_date, region, request_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS coupon_catalog (
          code String, active Bool, discount_type String, discount_value Float64
        ) ENGINE = ReplacingMergeTree ORDER BY code
        """,
        """
        CREATE TABLE IF NOT EXISTS etl_runs (
          loaded_at DateTime, source String, status LowCardinality(String),
          rows_sales UInt64, rows_purchases UInt64, rows_inventory UInt64,
          rows_logistics UInt64, message String
        ) ENGINE = MergeTree ORDER BY loaded_at
        """,
    ]
    for statement in statements:
        client.command(statement)
    # Migración suave para instalaciones que ya tenían fact_sales creada.
    client.command("ALTER TABLE fact_sales ADD COLUMN IF NOT EXISTS vendor_id UInt32 DEFAULT 0 AFTER category")
    client.command("ALTER TABLE fact_sales ADD COLUMN IF NOT EXISTS vendor String DEFAULT 'Sin proveedor' AFTER vendor_id")


def query_rows(sql: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = get_clickhouse_client().query(sql, parameters=parameters or {})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def ping_clickhouse() -> bool:
    try:
        return int(get_clickhouse_client().query("SELECT 1").first_row[0]) == 1
    except Exception:
        return False
