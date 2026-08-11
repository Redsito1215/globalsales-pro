"""Registro de tablas maestras editables (Q4 Datos)."""
from __future__ import annotations

from typing import Any

MASTER_TABLES: dict[str, dict[str, Any]] = {
    "dim_region": {
        "pk": "region_id",
        "label": "Regiones",
        "editable": True,
        "fields": ["region_id", "name", "description"],
    },
    "dim_pais": {
        "pk": "country_id",
        "label": "Países",
        "editable": True,
        "fields": ["country_id", "name", "region_id"],
        "fk": {"region_id": "dim_region"},
    },
    "dim_categoria": {
        "pk": "category_id",
        "label": "Categorías",
        "editable": True,
        "fields": ["category_id", "name", "description"],
    },
    "dim_producto": {
        "pk": "product_id",
        "label": "Productos",
        "editable": True,
        "image_field": "image_url",
        "fields": [
            "product_id",
            "name",
            "category_id",
            "line",
            "main_function",
            "weight_kg",
            "description",
            "unit_price",
            "unit_cost",
            "margin_pct",
            "image_url",
        ],
        "fk": {"category_id": "dim_categoria"},
    },
    "dim_canal": {
        "pk": "channel_id",
        "label": "Canales",
        "editable": True,
        "fields": ["channel_id", "name", "description"],
    },
    "dim_prioridad": {
        "pk": "priority_id",
        "label": "Prioridades",
        "editable": True,
        "fields": ["priority_id", "code", "name", "sla_days", "description"],
    },
    "dim_cliente": {
        "pk": "client_id",
        "label": "Clientes",
        "editable": True,
        "fields": ["client_id", "name", "country_id", "channel_id", "email", "phone", "created_at"],
        "fk": {"country_id": "dim_pais", "channel_id": "dim_canal"},
    },
    "dim_tiempo": {
        "pk": "tiempo_id",
        "label": "Tiempo",
        "editable": False,
        "fields": ["tiempo_id", "fecha_id", "anio", "mes", "trimestre"],
    },
}

EDITABLE_MASTERS = [k for k, v in MASTER_TABLES.items() if v.get("editable")]


def get_master(name: str) -> dict[str, Any] | None:
    return MASTER_TABLES.get(name)
