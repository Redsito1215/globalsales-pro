# -*- coding: utf-8 -*-
"""Qué colección vive en la base operativa vs data warehouse."""
from __future__ import annotations

# Sincronizado con shared.data_layers.LAYER_MAP (operativo + gobernanza → ops DB)
OPS_COLLECTIONS: frozenset[str] = frozenset(
    {
        "purchase_requests",
        "purchase_request_lines",
        "purchase_orders",
        "purchase_order_lines",
        "purchase_requisitions",
        "purchase_requisition_lines",
        "products",
        "product_variants",
        "product_media",
        "collections",
        "collection_products",
        "vendors",
        "warehouses",
        "inventory_items",
        "inventory_levels",
        "inventory_scrapped",
        "inventory_movements",
        "inventory_counts",
        "customers",
        "customer_addresses",
        "checkouts",
        "checkout_line_items",
        "discount_codes",
        "shop_settings",
        "support_messages",
        "user_notifications",
        "cash_movements",
        "invoices",
        "credit_notes",
        "accounting_periods",
        "payment_attempts",
        "request_events",
        "report_exports",
        "system_errors",
        "product_price_history",
        "discount_history",
        "commercial_exceptions",
        "users",
        "roles",
        "app_roles",
        "audit_log",
        "app_meta",
        "management_goals",
        "management_approvals",
    }
)


def is_ops_collection(name: str) -> bool:
    return name in OPS_COLLECTIONS
