# -*- coding: utf-8 -*-
"""Bodega única centralizada para todo el inventario operativo."""
from __future__ import annotations

from typing import Any

from shared.mongo import get_db

DEFAULT_WAREHOUSE_ID = 1
DEFAULT_WAREHOUSE_NAME = "Bodega General"
DEFAULT_WAREHOUSE_CODE = "BG-01"
LEGACY_WAREHOUSE_NAMES = frozenset({"Main Warehouse", "main warehouse"})


def ensure_default_warehouse() -> dict[str, Any]:
    """Garantiza una sola bodega activa y normaliza niveles de inventario legacy."""
    db = get_db()
    doc = {
        "warehouse_id": DEFAULT_WAREHOUSE_ID,
        "name": DEFAULT_WAREHOUSE_NAME,
        "code": DEFAULT_WAREHOUSE_CODE,
        "address": "Centro logístico GLOBTRADE — ubicación única",
        "is_default": True,
        "active": True,
    }
    db["warehouses"].update_one({"warehouse_id": DEFAULT_WAREHOUSE_ID}, {"$set": doc}, upsert=True)
    db["warehouses"].update_many(
        {"warehouse_id": {"$ne": DEFAULT_WAREHOUSE_ID}},
        {"$set": {"is_default": False, "active": False}},
    )
    for legacy in LEGACY_WAREHOUSE_NAMES:
        db["inventory_levels"].update_many({"location": legacy}, {"$set": {"location": DEFAULT_WAREHOUSE_NAME}})
    db["inventory_levels"].update_many(
        {"location": {"$exists": False}},
        {"$set": {"location": DEFAULT_WAREHOUSE_NAME}},
    )
    return doc


def warehouse_summary() -> dict[str, Any]:
    ensure_default_warehouse()
    return {
        "warehouse_id": DEFAULT_WAREHOUSE_ID,
        "name": DEFAULT_WAREHOUSE_NAME,
        "code": DEFAULT_WAREHOUSE_CODE,
        "address": "Centro logístico GLOBTRADE — ubicación única",
    }
