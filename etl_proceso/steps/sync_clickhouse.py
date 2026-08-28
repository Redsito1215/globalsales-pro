"""Publica el modelo analítico de MongoDB en ClickHouse (truncate + reload)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable

from shared.clickhouse import ensure_database_and_schema, get_clickhouse_client
from shared.mongo import get_dw_db, get_ops_db


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _date(value: Any, default: date | None = None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return default or date(1970, 1, 1)


def _insert(table: str, columns: list[str], rows: Iterable[tuple[Any, ...]], batch_size: int = 10_000) -> int:
    client = get_clickhouse_client()
    batch: list[tuple[Any, ...]] = []
    total = 0
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            client.insert(table, batch, column_names=columns)
            total += len(batch)
            batch.clear()
    if batch:
        client.insert(table, batch, column_names=columns)
        total += len(batch)
    return total


def _lookup(collection, key: str, label: str = "name") -> dict[Any, str]:
    return {row.get(key): str(row.get(label) or "—") for row in collection.find({}, {"_id": 0, key: 1, label: 1})}


def sync_clickhouse() -> dict[str, Any]:
    """Reconstruye las tablas analíticas. Mongo sigue siendo la fuente operativa."""
    ensure_database_and_schema()
    client = get_clickhouse_client()
    dw, ops = get_dw_db(), get_ops_db()
    tables = ["fact_sales", "fact_purchases", "inventory_snapshot", "fact_logistics", "coupon_catalog"]
    for table in tables:
        client.command(f"TRUNCATE TABLE {table}")

    categories = _lookup(dw["dim_categoria"], "category_id")
    regions = _lookup(dw["dim_region"], "region_id")
    countries = _lookup(dw["dim_pais"], "country_id")
    channels = _lookup(dw["dim_canal"], "channel_id")
    products = {
        row.get("product_id"): row
        for row in dw["dim_producto"].find({}, {"_id": 0, "product_id": 1, "name": 1, "category_id": 1})
    }
    ops_products = {
        int(row.get("product_id") or 0): row
        for row in ops["products"].find({}, {"_id": 0, "product_id": 1, "vendor_id": 1})
        if row.get("product_id") is not None
    }
    vendors = {
        int(row.get("vendor_id") or 0): str(row.get("name") or f"Proveedor {row.get('vendor_id')}")
        for row in ops["vendors"].find({}, {"_id": 0, "vendor_id": 1, "name": 1})
        if row.get("vendor_id") is not None
    }
    landing_by_order = {
        str(row.get("order_id") or ""): row
        for row in dw["sales_records"].find(
            {}, {"_id": 0, "order_id": 1, "product_id": 1, "product_name": 1, "discount_code": 1, "discount_alloc": 1}
        )
    }

    sales_columns = [
        "sale_id", "order_id", "sale_date", "product_id", "product", "category_id", "category",
        "vendor_id", "vendor", "region", "country", "channel", "units", "unit_price", "unit_cost", "revenue", "cost",
        "profit", "coupon", "discount",
    ]

    def sales_rows():
        for index, row in enumerate(dw["fact_ventas"].find({}, {"_id": 0}), 1):
            landing = landing_by_order.get(str(row.get("order_id") or ""), {})
            category_id = int(row.get("category_id") or 0)
            product_id = int(row.get("product_id") or landing.get("product_id") or 0)
            product = products.get(product_id) or {}
            ops_product = ops_products.get(product_id) or {}
            vendor_id = int(ops_product.get("vendor_id") or 0)
            vendor_name = vendors.get(vendor_id, "Sin proveedor" if vendor_id == 0 else f"Proveedor {vendor_id}")
            # Los históricos antiguos no traen product_id: se identifican claramente por categoría.
            product_name = str(product.get("name") or row.get("product_name") or landing.get("product_name") or f"Categoría: {categories.get(category_id, 'Sin categoría')}")
            yield (
                int(row.get("venta_id") or index), str(row.get("order_id") or ""), _date(row.get("fecha_id")),
                product_id, product_name, category_id, categories.get(category_id, "Sin categoría"),
                vendor_id, vendor_name,
                regions.get(row.get("region_id"), "—"), countries.get(row.get("country_id"), "—"),
                channels.get(row.get("channel_id"), "—"), _number(row.get("units_sold")),
                _number(row.get("unit_price")), _number(row.get("unit_cost")),
                _number(row.get("total_revenue") or row.get("line_revenue")),
                _number(row.get("total_cost") or row.get("line_cost")),
                _number(row.get("total_profit") or row.get("line_profit")),
                str(row.get("discount_code") or landing.get("discount_code") or ""),
                _number(row.get("discount_alloc") or landing.get("discount_alloc")),
            )

    sales_count = _insert("fact_sales", sales_columns, sales_rows())

    def purchase_rows():
        for row in ops["purchase_orders"].find({}, {"_id": 0}):
            amount = row.get("total")
            if amount is None:
                amount = sum(_number(line.get("quantity_ordered")) * _number(line.get("unit_cost")) for line in row.get("lines") or [])
            yield (
                str(row.get("po_id") or row.get("order_id") or ""),
                _date(row.get("received_at") or row.get("created_at")), str(row.get("status") or ""),
                str(row.get("vendor_name") or row.get("vendor_id") or "—"), _number(amount),
            )

    purchases_count = _insert("fact_purchases", ["purchase_id", "purchase_date", "status", "vendor", "amount"], purchase_rows())

    product_categories = {pid: int(row.get("category_id") or 0) for pid, row in products.items()}
    snapshot_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def inventory_rows():
        for row in ops["product_variants"].find({}, {"_id": 0}):
            pid = int(row.get("product_id") or 0)
            cid = product_categories.get(pid, 0)
            stock = _number(row.get("inventory_quantity"))
            unit_cost = _number(row.get("unit_cost") or row.get("cost"))
            yield (snapshot_at, pid, str((products.get(pid) or {}).get("name") or row.get("title") or f"Producto {pid}"), cid, categories.get(cid, "Sin categoría"), stock, stock * unit_cost)

    inventory_count = _insert("inventory_snapshot", ["snapshot_at", "product_id", "product", "category_id", "category", "stock", "inventory_value"], inventory_rows())

    def logistics_rows():
        for row in ops["purchase_requests"].find({}, {"_id": 0}):
            created = _date(row.get("created_at"))
            shipped_raw = row.get("shipped_at")
            shipped = _date(shipped_raw) if shipped_raw else None
            country_id = row.get("country_id")
            country = countries.get(country_id, "—")
            region_id = (dw["dim_pais"].find_one({"country_id": country_id}, {"_id": 0, "region_id": 1}) or {}).get("region_id")
            yield (str(row.get("request_id") or ""), created, shipped, regions.get(region_id, "—"), country, (shipped - created).days if shipped else None, str(row.get("status") or ""))

    logistics_count = _insert("fact_logistics", ["request_id", "created_date", "shipped_date", "region", "country", "days_to_ship", "status"], logistics_rows())

    def coupon_rows():
        for row in ops["discount_codes"].find({}, {"_id": 0}):
            yield (str(row.get("code") or ""), bool(row.get("active", True)), str(row.get("discount_type") or row.get("type") or ""), _number(row.get("value")))

    _insert("coupon_catalog", ["code", "active", "discount_type", "discount_value"], coupon_rows())
    counts = {
        "sales": sales_count, "purchases": purchases_count,
        "inventory": inventory_count, "logistics": logistics_count,
    }
    client.insert(
        "etl_runs",
        [(snapshot_at, "mongodb", "ok", sales_count, purchases_count, inventory_count, logistics_count, "Carga analítica completada")],
        column_names=["loaded_at", "source", "status", "rows_sales", "rows_purchases", "rows_inventory", "rows_logistics", "message"],
    )
    print(f"ClickHouse sincronizado: {counts}")
    return counts


if __name__ == "__main__":
    sync_clickhouse()
