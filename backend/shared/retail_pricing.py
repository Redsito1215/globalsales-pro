# -*- coding: utf-8 -*-
"""Precios de catálogo alineados a referencias B2B/retail (USD por unidad)."""
from __future__ import annotations

from typing import Any

# Referencias: IndexBox / retail US 2025-2026 (cereales ~5 USD, snacks ~3-5, bebidas ~4-6, etc.)
RETAIL_BASE_USD: dict[str, float] = {
    "Baby Food": 5.50,
    "Beverages": 4.25,
    "Cereal": 5.75,
    "Clothes": 22.00,
    "Cosmetics": 12.50,
    "Fruits": 3.50,
    "Household": 9.50,
    "Meat": 14.00,
    "Office Supplies": 6.50,
    "Personal Care": 8.25,
    "Snacks": 3.25,
    "Vegetables": 3.00,
}

_PRICE_FACTORS = (0.72, 0.82, 0.88, 0.94, 0.98, 1.02, 1.06, 1.12, 1.18, 1.28)
_COST_RATIO = 0.62


def retail_unit_price(category_name: str, line: int) -> tuple[float, float, float]:
    """Devuelve (unit_price, unit_cost, margin_pct) para una línea de catálogo."""
    base = RETAIL_BASE_USD.get(category_name, 8.0)
    idx = max(1, min(int(line or 1), len(_PRICE_FACTORS))) - 1
    unit_price = round(base * _PRICE_FACTORS[idx], 2)
    unit_cost = round(unit_price * _COST_RATIO, 2)
    margin = round(((unit_price - unit_cost) / unit_price * 100) if unit_price else 0, 2)
    return unit_price, unit_cost, margin


def patch_dim_producto_prices(db) -> int:
    """Actualiza dim_producto con precios retail (no depende del CSV histórico)."""
    updated = 0
    cats = {
        int(c["category_id"]): c.get("name")
        for c in db["dim_categoria"].find({}, {"category_id": 1, "name": 1})
    }
    for p in db["dim_producto"].find({}, {"product_id": 1, "category_id": 1, "line": 1}):
        cat_name = cats.get(int(p.get("category_id") or 0), "")
        line = int(p.get("line") or 1)
        up, uc, margin = retail_unit_price(cat_name, line)
        db["dim_producto"].update_one(
            {"product_id": int(p["product_id"])},
            {"$set": {"unit_price": up, "unit_cost": uc, "margin_pct": margin}},
        )
        updated += 1
    return updated


def price_summary(db) -> dict[str, Any]:
    rows = list(db["dim_producto"].find({}, {"unit_price": 1, "_id": 0}))
    prices = [float(r.get("unit_price") or 0) for r in rows if r.get("unit_price")]
    if not prices:
        return {"count": 0}
    return {
        "count": len(prices),
        "min": min(prices),
        "max": max(prices),
        "avg": round(sum(prices) / len(prices), 2),
    }
