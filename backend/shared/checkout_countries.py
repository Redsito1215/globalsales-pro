# -*- coding: utf-8 -*-
"""Países adicionales para checkout B2B (no siempre presentes en sales_records)."""
from __future__ import annotations

from typing import Any

from shared.mongo import get_db

# (nombre país, región comercial)
SUPPLEMENTAL_COUNTRIES: list[tuple[str, str]] = [
    ("Ecuador", "South America"),
    ("Colombia", "South America"),
    ("Peru", "South America"),
    ("Chile", "South America"),
    ("Argentina", "South America"),
    ("Brazil", "South America"),
    ("Bolivia", "South America"),
    ("Paraguay", "South America"),
    ("Uruguay", "South America"),
    ("Venezuela", "South America"),
    ("United States", "North America"),
]


def _next_id(col, pk: str) -> int:
    row = col.find_one({}, {pk: 1, "_id": 0}, sort=[(pk, -1)])
    if not row or row.get(pk) is None:
        return 1
    return int(row[pk]) + 1


def _ensure_region(db, name: str) -> int:
    doc = db["dim_region"].find_one({"name": name}, {"_id": 0, "region_id": 1})
    if doc:
        return int(doc["region_id"])
    rid = _next_id(db["dim_region"], "region_id")
    db["dim_region"].insert_one(
        {"region_id": rid, "name": name, "description": f"Zona comercial: {name}"}
    )
    return rid


def ensure_checkout_countries() -> int:
    """Inserta países B2B que falten en dim_pais. Devuelve cuántos se añadieron."""
    db = get_db()
    region_ids: dict[str, int] = {}
    added = 0
    for country_name, region_name in SUPPLEMENTAL_COUNTRIES:
        if db["dim_pais"].find_one({"name": country_name}, {"_id": 1}):
            continue
        if region_name not in region_ids:
            region_ids[region_name] = _ensure_region(db, region_name)
        cid = _next_id(db["dim_pais"], "country_id")
        db["dim_pais"].insert_one(
            {
                "country_id": cid,
                "name": country_name,
                "region_id": region_ids[region_name],
            }
        )
        added += 1
    return added


def list_checkout_countries(*, limit: int = 500) -> dict[str, Any]:
    ensure_checkout_countries()
    db = get_db()
    col = db["dim_pais"]
    total = col.count_documents({})
    rows = list(
        col.find({}, {"_id": 0, "country_id": 1, "name": 1, "region_id": 1})
        .sort("name", 1)
        .limit(limit)
    )
    return {"total": total, "limit": limit, "countries": rows}
