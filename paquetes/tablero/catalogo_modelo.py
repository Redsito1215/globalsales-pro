"""Modelo catálogo: N productos por category_id; totales cuadran con sales_records."""
from __future__ import annotations

import hashlib
from typing import Any

from paquetes.tablero import catalogo_nombres as nombres
from shared.mongo import get_db, sales_collection
from shared.retail_pricing import retail_unit_price

PRODUCTS_PER_CATEGORY = 10

CATEGORY_DESC: dict[str, str] = {
    "Baby Food": "Alimentos para bebés",
    "Beverages": "Bebidas y líquidos",
    "Cereal": "Cereales y granos",
    "Clothes": "Prendas de vestir y moda",
    "Cosmetics": "Productos de belleza y cuidado facial",
    "Fruits": "Frutas frescas e importadas",
    "Household": "Artículos del hogar",
    "Meat": "Carnes y derivados",
    "Office Supplies": "Insumos de oficina",
    "Personal Care": "Higiene y cuidado personal",
    "Snacks": "Productos de botana y snacks envasados",
    "Vegetables": "Verduras y hortalizas",
}

# Precios distintos por línea; media ≈ 1.0 respecto al precio base de la categoría
_PRICE_FACTORS = (0.72, 0.82, 0.88, 0.94, 0.98, 1.02, 1.06, 1.12, 1.18, 1.28)


def _line_weight(category_id: int, line: int) -> float:
    h = hashlib.md5(f"{category_id}:{line}".encode()).hexdigest()
    return 0.85 + (int(h[:8], 16) % 300) / 1000.0


def _allocate_int(total: int, category_id: int, field: str) -> list[int]:
    weights = [_line_weight(category_id, i + 1) for i in range(PRODUCTS_PER_CATEGORY)]
    s = sum(weights)
    weights = [w / s for w in weights]
    parts = [int(total * w) for w in weights]
    diff = total - sum(parts)
    i = 0
    while diff != 0:
        idx = i % PRODUCTS_PER_CATEGORY
        if diff > 0:
            parts[idx] += 1
            diff -= 1
        elif parts[idx] > 0:
            parts[idx] -= 1
            diff += 1
        i += 1
    return parts


def category_stats(item_type: str) -> dict[str, Any]:
    rows = list(
        sales_collection().aggregate(
            [
                {"$match": {"item_type": item_type}},
                {
                    "$group": {
                        "_id": None,
                        "revenue": {"$sum": "$total_revenue"},
                        "units": {"$sum": "$units_sold"},
                        "orders": {"$sum": 1},
                        "unit_price": {"$avg": "$unit_price"},
                        "unit_cost": {"$avg": "$unit_cost"},
                    }
                },
            ]
        )
    )
    x = rows[0] if rows else {}
    return {
        "revenue": float(x.get("revenue") or 0),
        "units": int(x.get("units") or 0),
        "orders": int(x.get("orders") or 0),
        "unit_price": float(x.get("unit_price") or 0),
        "unit_cost": float(x.get("unit_cost") or 0),
    }


def build_products_for_category(
    category_id: int,
    category_name: str,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """10 SKUs oficiales por category_id; totales repartidos desde sales_records."""
    defs = nombres.products_for_category(category_id)
    if len(defs) != PRODUCTS_PER_CATEGORY:
        raise ValueError(f"Categoría {category_id}: se esperaban {PRODUCTS_PER_CATEGORY} productos")

    stats = stats or category_stats(category_name)
    total_rev = stats["revenue"]
    total_units = stats["units"]
    total_orders = stats["orders"]

    units_parts = _allocate_int(total_units, category_id, "units")
    orders_parts = _allocate_int(total_orders, category_id, "orders")

    products: list[dict[str, Any]] = []
    revenue_running = 0.0

    for line, defn in enumerate(defs, start=1):
        unit_price, unit_cost, margin = retail_unit_price(category_name, line)
        units = units_parts[line - 1]
        orders = orders_parts[line - 1]

        if line < PRODUCTS_PER_CATEGORY:
            revenue = round(units * unit_price, 2)
        else:
            revenue = round(total_rev - revenue_running, 2)

        revenue_running += revenue

        products.append(
            {
                "product_id": int(defn["product_id"]),
                "category_id": category_id,
                "line": line,
                "category": category_name,
                "name": defn["name"],
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "margin_pct": margin,
                "units": units,
                "orders": orders,
                "revenue": revenue,
            }
        )

    return products


def load_category_map() -> list[dict[str, Any]]:
    db = get_db()
    rows = list(db["dim_categoria"].find({}, {"_id": 0}).sort("category_id", 1))
    if rows:
        return rows
    types = sorted(sales_collection().distinct("item_type"))
    return [{"category_id": i + 1, "name": n, "description": ""} for i, n in enumerate(types)]


def build_full_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for cid in sorted(nombres.CATEGORY_BY_ID.keys()):
        name = nombres.category_name(cid)
        catalog.extend(build_products_for_category(cid, name))
    return catalog


def verify_category_totals(category_name: str) -> dict[str, Any]:
    """Comprueba que la suma de las 10 líneas ≈ total en sales_records."""
    cats = {c["name"]: c for c in load_category_map()}
    cat = cats.get(category_name)
    if not cat:
        return {"ok": False, "error": "categoría no encontrada"}
    cid = int(cat["category_id"])
    stats = category_stats(category_name)
    products = build_products_for_category(cid, category_name, stats)
    sum_rev = sum(p["revenue"] for p in products)
    sum_units = sum(p["units"] for p in products)
    return {
        "ok": abs(sum_rev - stats["revenue"]) < 1.0,
        "category": category_name,
        "category_id": cid,
        "expected_revenue": stats["revenue"],
        "catalog_revenue": round(sum_rev, 2),
        "expected_units": stats["units"],
        "catalog_units": sum_units,
        "products": len(products),
    }
