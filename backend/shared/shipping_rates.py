# -*- coding: utf-8 -*-
"""Tarifas de envío estimadas para pedidos online (USD)."""
from __future__ import annotations

from typing import Any

# Tarifas demo por región comercial (base + kg + ítem)
_REGION_RATES: dict[str, dict[str, float]] = {
    "South America": {"base": 5.50, "per_kg": 1.10, "per_item": 0.45},
    "North America": {"base": 11.00, "per_kg": 2.20, "per_item": 0.85},
    "Europe": {"base": 16.00, "per_kg": 2.80, "per_item": 1.00},
    "Asia": {"base": 18.50, "per_kg": 3.10, "per_item": 1.10},
    "Africa": {"base": 17.00, "per_kg": 2.90, "per_item": 1.05},
    "Oceania": {"base": 19.00, "per_kg": 3.20, "per_item": 1.15},
    "default": {"base": 14.00, "per_kg": 2.50, "per_item": 0.90},
}

_CATEGORY_WEIGHT_KG: dict[str, tuple[float, float]] = {
    "Baby Food": (0.12, 0.45),
    "Beverages": (0.35, 2.0),
    "Cereal": (0.25, 1.5),
    "Clothes": (0.15, 0.9),
    "Cosmetics": (0.05, 0.35),
    "Fruits": (0.08, 1.2),
    "Household": (0.2, 4.5),
    "Meat": (0.25, 1.8),
    "Office Supplies": (0.05, 2.5),
    "Personal Care": (0.08, 0.6),
    "Snacks": (0.05, 0.8),
    "Vegetables": (0.1, 1.5),
}


def _line_weight_kg(db, product_id: int, category_name: str) -> float:
    dim = db["dim_producto"].find_one({"product_id": int(product_id)}, {"weight_kg": 1, "line": 1, "category_id": 1})
    if dim and dim.get("weight_kg") is not None:
        return float(dim["weight_kg"])
    if not category_name:
        cat = db["dim_categoria"].find_one({"category_id": dim.get("category_id") if dim else None}, {"name": 1})
        category_name = (cat or {}).get("name") or ""
    lo, hi = _CATEGORY_WEIGHT_KG.get(category_name, (0.15, 1.0))
    line = int((dim or {}).get("line") or 1)
    frac = ((line * 17) % 100) / 100.0
    return round(lo + (hi - lo) * frac, 3)


def region_name_for_country(db, country_id: int) -> str:
    country = db["dim_pais"].find_one({"country_id": int(country_id)}, {"region_id": 1, "name": 1})
    if not country:
        return "default"
    region = db["dim_region"].find_one({"region_id": country.get("region_id")}, {"name": 1})
    return (region or {}).get("name") or "default"


def shipping_quote(db, *, country_id: int, lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula envío para líneas {variant_id|product_id, quantity}."""
    region = region_name_for_country(db, country_id)
    rates = _REGION_RATES.get(region, _REGION_RATES["default"])
    total_items = 0
    total_kg = 0.0
    for item in lines or []:
        qty = int(item.get("quantity") or 0)
        if qty < 1:
            continue
        vid = int(item.get("variant_id") or item.get("product_id") or 0)
        variant = db["product_variants"].find_one({"variant_id": vid}) or db["product_variants"].find_one(
            {"product_id": vid}
        )
        if not variant:
            continue
        pid = int(variant["product_id"])
        prod = db["products"].find_one({"product_id": pid}, {"product_type": 1}) or {}
        cat_name = prod.get("product_type") or ""
        w = _line_weight_kg(db, pid, cat_name)
        total_items += qty
        total_kg += w * qty

    cost = rates["base"] + rates["per_kg"] * total_kg + rates["per_item"] * total_items
    country = db["dim_pais"].find_one({"country_id": int(country_id)}, {"name": 1})
    return {
        "shipping_cost": round(max(cost, 0.0), 2),
        "region_name": region,
        "country_name": (country or {}).get("name"),
        "total_weight_kg": round(total_kg, 2),
        "total_items": total_items,
        "rate_base": rates["base"],
    }


def is_online_channel(db, channel_id: int) -> bool:
    ch = db["dim_canal"].find_one({"channel_id": int(channel_id)}, {"name": 1})
    name = (ch or {}).get("name") or ""
    return name.strip().lower() == "online" or int(channel_id) == 1
