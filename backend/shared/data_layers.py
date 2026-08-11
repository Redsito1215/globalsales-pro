# -*- coding: utf-8 -*-
"""Capas de datos: operativo (OLTP) vs landing vs estratégico (DW)."""
from __future__ import annotations

from typing import Any

from shared.mongo import get_db, get_ops_db, get_dw_db, mongo_topology

# colección → capa
LAYER_MAP: dict[str, str] = {
    # Operativo (transaccional)
    "purchase_requests": "operativo",
    "purchase_request_lines": "operativo",
    "purchase_orders": "operativo",
    "purchase_order_lines": "operativo",
    "products": "operativo",
    "product_variants": "operativo",
    "product_media": "operativo",
    "collections": "operativo",
    "collection_products": "operativo",
    "vendors": "operativo",
    "warehouses": "operativo",
    "inventory_items": "operativo",
    "inventory_levels": "operativo",
    "inventory_scrapped": "operativo",
    "customers": "operativo",
    "customer_addresses": "operativo",
    "checkouts": "operativo",
    "checkout_line_items": "operativo",
    "discount_codes": "operativo",
    "shop_settings": "operativo",
    "support_messages": "operativo",
    "user_notifications": "operativo",
    # Landing (staging / CSV / post-convertir)
    "sales_records": "landing",
    "orders": "landing",
    "order_lines": "landing",
    # Estratégico (estrella)
    "fact_ventas": "estrategico",
    "monthly_kpis": "estrategico",
    # Dimensiones
    "dim_region": "dimension",
    "dim_pais": "dimension",
    "dim_categoria": "dimension",
    "dim_producto": "dimension",
    "dim_canal": "dimension",
    "dim_prioridad": "dimension",
    "dim_cliente": "dimension",
    "dim_tiempo": "dimension",
    # Gobernanza
    "audit_log": "gobernanza",
    "users": "gobernanza",
    "roles": "gobernanza",
    "app_roles": "gobernanza",
    "app_meta": "gobernanza",
    # Espejos SQL / legacy (ELT)
    "regions": "dimension",
    "countries": "dimension",
    "clients": "dimension",
    "sales_channels": "dimension",
    "order_priorities": "dimension",
}

LAYER_LABELS: dict[str, str] = {
    "operativo": "Operativo (transaccional)",
    "landing": "Landing / staging",
    "estrategico": "Estratégico (DW)",
    "dimension": "Dimensiones",
    "gobernanza": "Gobernanza",
}


def ops_db():
    """Base operativa (OLTP + gobernanza)."""
    return get_ops_db()


def landing_sales():
    """Staging: CSV, generate y post-convertir."""
    return get_db()["sales_records"]


def analytics_fact():
    """Hechos del modelo estrella."""
    return get_db()["fact_ventas"]


def ops_collection(name: str):
    """Colección operativa (validada)."""
    if LAYER_MAP.get(name) != "operativo":
        raise ValueError(f"not_ops_collection:{name}")
    return ops_db()[name]


def strategic_ready() -> bool:
    try:
        return analytics_fact().estimated_document_count() > 0 or analytics_fact().count_documents({}, limit=1) > 0
    except Exception:
        return False


def _last_build_at(db) -> str | None:
    """Último build_model / carga ELT en audit_log, si existe."""
    try:
        doc = db["audit_log"].find_one(
            {"action": {"$in": ["build_model", "load_dataset"]}},
            {"at": 1, "action": 1, "_id": 0},
            sort=[("at", -1)],
        )
        if not doc:
            return None
        return doc.get("at")
    except Exception:
        return None


def layers_overview() -> dict[str, Any]:
    """Resumen para meta API / demo académica."""
    by_layer: dict[str, list[dict[str, Any]]] = {k: [] for k in LAYER_LABELS}
    for coll, layer in sorted(LAYER_MAP.items()):
        try:
            db = get_ops_db() if layer in ("operativo", "gobernanza") else get_dw_db()
            n = db[coll].estimated_document_count()
        except Exception:
            n = 0
        by_layer.setdefault(layer, []).append({"name": coll, "count": int(n)})

    dw = get_dw_db()
    ready = strategic_ready()
    fact_n = 0
    landing_n = 0
    try:
        fact_n = int(dw["fact_ventas"].estimated_document_count())
        landing_n = int(dw["sales_records"].estimated_document_count())
    except Exception:
        pass

    last_build = _last_build_at(get_ops_db())
    lag: dict[str, Any] = {}
    try:
        from shared.analytics_sync import get_strategic_lag

        lag = get_strategic_lag()
    except Exception:
        lag = {"strategic_lagging": False}

    lagging = bool(lag.get("strategic_lagging"))
    msg = (
        "Capa estratégica vacía: ejecuta Datos → Carga ELT o Construir modelo."
        if not ready
        else (
            "Hay ventas en landing sin sincronizar a fact_ventas."
            if lagging
            else "Capa estratégica lista (fact_ventas)."
        )
    )
    return {
        "layers": [
            {
                "id": lid,
                "label": LAYER_LABELS[lid],
                "collections": by_layer.get(lid, []),
            }
            for lid in ("operativo", "landing", "estrategico", "dimension", "gobernanza")
            if lid in LAYER_LABELS
        ],
        "strategic_ready": ready,
        "strategic_lagging": lagging,
        "missing_sample": lag.get("missing_sample") or [],
        "fact_ventas_count": fact_n,
        "sales_records_count": landing_n,
        "last_build": last_build,
        "bridge": {
            "from": "operativo.purchase_requests",
            "via": "convertir → landing.sales_records → sync incremental",
            "to": "estrategico.fact_ventas (append o build_model)",
        },
        "message": msg,
        "topology": mongo_topology(),
    }
