# -*- coding: utf-8 -*-
"""Índices Mongo para colecciones operativas (consultas del día a día)."""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING

from shared.mongo import get_db


def ensure_ops_indexes() -> dict[str, int]:
    """Crea índices idempotentes. Devuelve cuántos se aseguraron por colección."""
    db = get_db()
    created: dict[str, int] = {}

    specs: list[tuple[str, list, dict]] = [
        ("purchase_requests", [("status", ASCENDING), ("request_id", DESCENDING)], {"name": "pr_status_id"}),
        ("purchase_requests", [("client_email", ASCENDING), ("request_id", DESCENDING)], {"name": "pr_client_email"}),
        ("purchase_requests", [("created_at", DESCENDING)], {"name": "pr_created"}),
        ("purchase_request_lines", [("request_id", ASCENDING)], {"name": "prl_request"}),
        ("product_variants", [("inventory_quantity", ASCENDING)], {"name": "pv_stock"}),
        ("product_variants", [("product_id", ASCENDING)], {"name": "pv_product"}),
        ("product_variants", [("sku", ASCENDING)], {"name": "pv_sku"}),
        ("products", [("vendor_id", ASCENDING)], {"name": "prod_vendor"}),
        ("purchase_orders", [("status", ASCENDING), ("po_id", DESCENDING)], {"name": "po_status_id"}),
        ("purchase_order_lines", [("po_id", ASCENDING)], {"name": "pol_po"}),
        ("vendors", [("active", ASCENDING), ("vendor_id", ASCENDING)], {"name": "vendors_active"}),
        ("user_notifications", [("recipient_email", ASCENDING), ("notification_id", DESCENDING)], {"name": "notif_inbox"}),
        ("user_notifications", [("recipient_email", ASCENDING), ("read", ASCENDING)], {"name": "notif_unread"}),
        ("support_messages", [("thread_email", ASCENDING), ("message_id", DESCENDING)], {"name": "support_thread"}),
        ("sales_records", [("order_id", ASCENDING)], {"name": "sales_order"}),
        ("sales_records", [("order_date", DESCENDING)], {"name": "sales_order_date"}),
        ("sales_records", [("region", ASCENDING), ("order_date", DESCENDING)], {"name": "sales_region_date"}),
        ("sales_records", [("item_type", ASCENDING), ("order_date", DESCENDING)], {"name": "sales_item_date"}),
        ("sales_records", [("sales_channel", ASCENDING)], {"name": "sales_channel"}),
        ("sales_records", [("order_priority", ASCENDING)], {"name": "sales_priority"}),
        ("sales_records", [("country", ASCENDING), ("order_date", DESCENDING)], {"name": "sales_country_date"}),
        ("inventory_scrapped", [("request_id", ASCENDING)], {"name": "scrap_request"}),
        ("audit_log", [("at", DESCENDING)], {"name": "audit_at"}),
        ("audit_log", [("role", ASCENDING), ("at", DESCENDING)], {"name": "audit_role_at"}),
        # Estratégico (hechos)
        ("fact_ventas", [("fecha_id", DESCENDING)], {"name": "fact_fecha"}),
        ("fact_ventas", [("order_id", ASCENDING)], {"name": "fact_order"}),
        ("fact_ventas", [("region_id", ASCENDING), ("fecha_id", DESCENDING)], {"name": "fact_region_fecha"}),
        ("fact_ventas", [("category_id", ASCENDING), ("fecha_id", DESCENDING)], {"name": "fact_cat_fecha"}),
        ("fact_ventas", [("channel_id", ASCENDING)], {"name": "fact_channel"}),
        ("fact_ventas", [("channel_id", ASCENDING), ("fecha_id", DESCENDING)], {"name": "fact_channel_fecha"}),
        ("fact_ventas", [("country_id", ASCENDING), ("fecha_id", DESCENDING)], {"name": "fact_country_fecha"}),
        ("fact_ventas", [("priority_id", ASCENDING), ("fecha_id", DESCENDING)], {"name": "fact_priority_fecha"}),
        ("fact_ventas", [("venta_id", DESCENDING)], {"name": "fact_venta_id"}),
        ("dim_region", [("name", ASCENDING)], {"name": "dim_region_name"}),
        ("dim_categoria", [("name", ASCENDING)], {"name": "dim_categoria_name"}),
        ("dim_canal", [("name", ASCENDING)], {"name": "dim_canal_name"}),
        ("dim_prioridad", [("code", ASCENDING)], {"name": "dim_prioridad_code"}),
        ("dim_pais", [("name", ASCENDING)], {"name": "dim_pais_name"}),
        ("dim_producto", [("category_id", ASCENDING), ("product_id", ASCENDING)], {"name": "dim_prod_cat"}),
        ("dim_tiempo", [("fecha_id", ASCENDING)], {"name": "dim_tiempo_fecha"}),
        ("collection_products", [("collection_id", ASCENDING)], {"name": "cp_collection"}),
        ("products", [("status", ASCENDING), ("product_id", ASCENDING)], {"name": "prod_status_id"}),
        ("monthly_kpis", [("year", ASCENDING), ("month", ASCENDING)], {"name": "mkpi_ym"}),
    ]

    for coll, keys, opts in specs:
        try:
            db[coll].create_index(keys, **opts)
            created[coll] = created.get(coll, 0) + 1
        except Exception:
            # Índice ya existe con otro nombre u opciones incompatibles: no bloquea arranque
            pass
    return created
