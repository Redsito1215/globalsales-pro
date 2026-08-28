"""Registro de tablas maestras editables (Q4 Datos / Gestión)."""
from __future__ import annotations

from typing import Any

FIELD_LABELS: dict[str, str] = {
    "region_id": "Región",
    "country_id": "País",
    "category_id": "Categoría",
    "product_id": "ID producto",
    "channel_id": "Canal",
    "priority_id": "ID prioridad",
    "client_id": "ID cliente",
    "tiempo_id": "ID tiempo",
    "name": "Nombre",
    "description": "Descripción",
    "code": "Código",
    "sla_days": "Días SLA",
    "line": "Línea",
    "main_function": "Función",
    "weight_kg": "Peso (kg)",
    "unit_price": "Precio unitario",
    "unit_cost": "Costo unitario",
    "margin_pct": "Margen %",
    "sale_enabled": "Rebaja activa",
    "sale_percent": "Rebaja %",
    "image_url": "Imagen",
    "email": "Correo",
    "phone": "Teléfono",
    "created_at": "Creado",
    "active": "Estado",
    "fecha_id": "Fecha",
    "anio": "Año",
    "mes": "Mes",
    "trimestre": "Trimestre",
}

MASTER_TABLES: dict[str, dict[str, Any]] = {
    "dim_region": {
        "pk": "region_id",
        "label": "Regiones",
        "description": "Macrozonas geográficas (continentes) usadas en ventas y análisis.",
        "editable": True,
        "fields": ["region_id", "name", "description", "active"],
    },
    "dim_pais": {
        "pk": "country_id",
        "label": "Países",
        "description": "Países de operación vinculados a una región.",
        "editable": True,
        "fields": ["country_id", "name", "region_id", "active"],
        "fk": {"region_id": "dim_region"},
    },
    "dim_categoria": {
        "pk": "category_id",
        "label": "Categorías",
        "description": "Familias de producto; la clave en inglés se conserva en el almacén para el ETL.",
        "editable": True,
        "fields": ["category_id", "name", "description", "sale_enabled", "sale_percent", "active"],
    },
    "dim_producto": {
        "pk": "product_id",
        "label": "Productos",
        "description": "Catálogo analítico de SKUs; sincroniza vitrina e inventario al guardar.",
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
            "sale_enabled",
            "sale_percent",
            "featured",
            "image_url",
            "active",
        ],
        "fk": {"category_id": "dim_categoria"},
    },
    "dim_canal": {
        "pk": "channel_id",
        "label": "Canales",
        "description": "Canales de venta (online, retail, distribuidor, etc.).",
        "editable": True,
        "fields": ["channel_id", "name", "description", "active"],
    },
    "dim_prioridad": {
        "pk": "priority_id",
        "label": "Prioridades",
        "description": "Niveles de prioridad logística y SLA asociado.",
        "editable": True,
        "fields": ["priority_id", "code", "name", "sla_days", "description", "active"],
    },
    "dim_cliente": {
        "pk": "client_id",
        "label": "Clientes",
        "description": "Clientes B2B del modelo dimensional.",
        "editable": True,
        "fields": ["client_id", "name", "country_id", "channel_id", "email", "phone", "segment", "purchase_limit", "credit_limit", "credit_days", "credit_enabled", "created_at", "active"],
        "fk": {"country_id": "dim_pais", "channel_id": "dim_canal"},
    },
    "dim_tiempo": {
        "pk": "tiempo_id",
        "label": "Tiempo",
        "description": "Calendario generado por la carga ELT (solo lectura).",
        "editable": False,
        "fields": ["tiempo_id", "fecha_id", "anio", "mes", "trimestre"],
    },
}

EDITABLE_MASTERS = [k for k, v in MASTER_TABLES.items() if v.get("editable")]

# Catálogos oficiales: se pueden corregir e inhabilitar, pero no ampliar desde Gestión.
FIXED_MASTERS = {"dim_region", "dim_pais", "dim_canal", "dim_prioridad"}


def get_master(name: str) -> dict[str, Any] | None:
    return MASTER_TABLES.get(name)


def master_allows_create(name: str) -> bool:
    return name in EDITABLE_MASTERS and name not in FIXED_MASTERS


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
