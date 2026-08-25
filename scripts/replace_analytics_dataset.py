"""Reemplaza el histórico analítico por una serie continua y coherente de 2 M filas."""
from __future__ import annotations

import argparse
import calendar
import math
import os
import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

START_MONTH = date(2010, 1, 1)
DEFAULT_END = date(2026, 8, 24)
BATCH_SIZE = 10_000


def month_starts(start: date, end: date) -> list[date]:
    months, current = [], start.replace(day=1)
    last = end.replace(day=1)
    while current <= last:
        months.append(current)
        current = date(current.year + (current.month == 12), 1 if current.month == 12 else current.month + 1, 1)
    return months


def allocate_monthly_counts(total: int, months: list[date]) -> list[int]:
    """Distribución exacta con crecimiento y estacionalidad suaves, sin saltos aleatorios."""
    seasonal = (0.94, 0.95, 0.98, 1.00, 1.02, 1.01, 0.99, 1.00, 1.03, 1.05, 1.10, 1.16)
    weights = []
    denominator = max(len(months) - 1, 1)
    for index, month in enumerate(months):
        trend = 0.88 + 0.24 * (index / denominator)
        cycle = 1.0 + 0.018 * math.sin(index * math.pi / 18)
        weights.append(trend * seasonal[month.month - 1] * cycle)
    raw = [total * weight / sum(weights) for weight in weights]
    counts = [int(value) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)[: total - sum(counts)]:
        counts[index] += 1
    return counts


def _catalogs(db: Any) -> dict[str, Any]:
    regions = {int(r["region_id"]): r["name"] for r in db.dim_region.find({"active": {"$ne": False}})}
    countries = [
        {"id": int(row["country_id"]), "name": row["name"], "region_id": int(row["region_id"]), "region": regions[int(row["region_id"])]}
        for row in db.dim_pais.find({"active": {"$ne": False}}) if int(row.get("region_id") or 0) in regions
    ]
    categories = [
        {"id": int(row["category_id"]), "name": row["name"]}
        for row in db.dim_categoria.find({"active": {"$ne": False}}).sort("category_id", 1)
    ]
    channels = [
        {"id": int(row["channel_id"]), "name": row["name"]}
        for row in db.dim_canal.find({"active": {"$ne": False}})
    ]
    priorities = [
        {"id": int(row["priority_id"]), "code": row.get("code") or str(row.get("name", "M"))[:1]}
        for row in db.dim_prioridad.find({"active": {"$ne": False}})
    ]
    products: dict[int, list[dict]] = defaultdict(list)
    for row in db.dim_producto.find({"active": {"$ne": False}}):
        products[int(row["category_id"])].append(row)
    if not countries or not categories or not channels or not priorities:
        raise RuntimeError("Faltan dimensiones activas para generar el histórico.")
    clients = {(country["id"], channel["id"]): index + 1 for index, (country, channel) in enumerate(
        (pair for pair in ((c, ch) for c in countries for ch in channels))
    )}
    return {"countries": countries, "categories": categories, "channels": channels, "priorities": priorities, "products": products, "clients": clients}


def _flush(collection, rows: list[dict]) -> None:
    if rows:
        collection.insert_many(rows, ordered=False)
        rows.clear()


def build_dataset(db: Any, *, total: int, end: date, seed: int = 20260824) -> dict[str, Any]:
    random.seed(seed)
    catalogs = _catalogs(db)
    months = month_starts(START_MONTH, end)
    counts = allocate_monthly_counts(total, months)
    sales_name, facts_name, kpis_name = "sales_records_next", "fact_ventas_next", "monthly_kpis_next"
    for name in (sales_name, facts_name, kpis_name):
        db.drop_collection(name)
    sales, facts, kpis = db[sales_name], db[facts_name], db[kpis_name]
    sales_batch: list[dict] = []
    facts_batch: list[dict] = []
    monthly: dict[tuple, dict[str, Any]] = {}
    order_id = 1

    for month_index, (month, count) in enumerate(zip(months, counts)):
        max_day = end.day if month.year == end.year and month.month == end.month else calendar.monthrange(month.year, month.month)[1]
        month_progress = month_index / max(len(months) - 1, 1)
        for month_row in range(count):
            country = random.choice(catalogs["countries"])
            category = random.choice(catalogs["categories"])
            channel = random.choices(catalogs["channels"], weights=[62 if c["name"] == "Online" else 38 for c in catalogs["channels"]], k=1)[0]
            priority = random.choices(catalogs["priorities"], weights=[8, 22, 48, 22][:len(catalogs["priorities"])], k=1)[0]
            product_pool = catalogs["products"].get(category["id"]) or [{}]
            product = random.choice(product_pool)
            base_price = float(product.get("unit_price") or (18 + category["id"] * 7.5))
            base_cost = float(product.get("unit_cost") or base_price * 0.68)
            units = max(1, min(160, int(random.lognormvariate(3.25 + month_progress * 0.08, 0.55))))
            unit_price = round(base_price * random.uniform(0.96, 1.04) * (1 + month_progress * 0.12), 2)
            margin = min(0.44, max(0.18, 1 - base_cost / max(base_price, 0.01) + random.uniform(-0.025, 0.025)))
            unit_cost = round(unit_price * (1 - margin), 2)
            revenue = round(units * unit_price, 2)
            cost = round(units * unit_cost, 2)
            profit = round(revenue - cost, 2)
            forced_day = 1 if month_index == 0 and month_row == 0 else max_day if month_index == len(months) - 1 and month_row == count - 1 else None
            order_date = date(month.year, month.month, forced_day or random.randint(1, max_day))
            ship_date = min(order_date + timedelta(days=random.randint(1, 14)), end)
            oid = str(order_id)
            sale = {
                "order_id": oid, "region": country["region"], "country": country["name"],
                "item_type": category["name"], "sales_channel": channel["name"],
                "order_priority": priority["code"], "order_date": order_date.isoformat(),
                "ship_date": ship_date.isoformat(), "units_sold": units, "unit_price": unit_price,
                "unit_cost": unit_cost, "total_revenue": revenue, "total_cost": cost,
                "total_profit": profit, "id": f"gt-{order_id:09d}", "dataset_version": "normalized-2026-08",
            }
            fact = {
                "venta_id": order_id, "order_id": oid, "fecha_id": order_date.isoformat(),
                "region_id": country["region_id"], "country_id": country["id"],
                "category_id": category["id"], "channel_id": channel["id"],
                "priority_id": priority["id"], "client_id": catalogs["clients"][(country["id"], channel["id"])],
                "units_sold": units, "unit_price": unit_price, "unit_cost": unit_cost,
                "total_revenue": revenue, "total_cost": cost, "total_profit": profit,
                "line_revenue": revenue, "line_cost": cost, "line_profit": profit,
            }
            sales_batch.append(sale)
            facts_batch.append(fact)
            key = (month.year, month.month, country["region"], category["name"])
            item = monthly.setdefault(key, {"orders": 0, "units": 0, "revenue": 0.0, "cost": 0.0, "profit": 0.0})
            item["orders"] += 1; item["units"] += units; item["revenue"] += revenue; item["cost"] += cost; item["profit"] += profit
            order_id += 1
            if len(sales_batch) >= BATCH_SIZE:
                _flush(sales, sales_batch); _flush(facts, facts_batch)
        print(f"{month.isoformat()[:7]}: {count:,} ({order_id - 1:,}/{total:,})", flush=True)
    _flush(sales, sales_batch); _flush(facts, facts_batch)

    kpi_rows = []
    for kpi_id, ((year, month, region, item_type), values) in enumerate(sorted(monthly.items()), 1):
        revenue, profit = values["revenue"], values["profit"]
        kpi_rows.append({
            "kpi_id": kpi_id, "year": year, "month": month, "region": region, "item_type": item_type,
            "total_orders": values["orders"], "total_units": values["units"],
            "total_revenue": round(revenue, 2), "total_cost": round(values["cost"], 2),
            "total_profit": round(profit, 2), "avg_margin_pct": round(profit / revenue * 100, 2) if revenue else 0,
        })
    _flush(kpis, kpi_rows)

    sales.create_index([("order_id", ASCENDING)], name="sales_order")
    sales.create_index([("order_date", DESCENDING)], name="sales_order_date")
    sales.create_index([("region", ASCENDING), ("order_date", DESCENDING)], name="sales_region_date")
    facts.create_index([("venta_id", ASCENDING)], unique=True, name="fact_venta_id")
    facts.create_index([("fecha_id", DESCENDING)], name="fact_fecha")
    facts.create_index([("region_id", ASCENDING), ("fecha_id", DESCENDING)], name="fact_region_fecha")

    if sales.estimated_document_count() != total or facts.estimated_document_count() != total:
        raise RuntimeError("La validación de conteos temporales falló; no se reemplazó ninguna colección.")
    first = sales.find_one(sort=[("order_date", ASCENDING)])["order_date"]
    last = sales.find_one(sort=[("order_date", DESCENDING)])["order_date"]
    if first != START_MONTH.isoformat() or last != end.isoformat():
        raise RuntimeError(f"Rango temporal inválido: {first} a {last}.")

    for current, replacement in (("sales_records", sales_name), ("fact_ventas", facts_name), ("monthly_kpis", kpis_name)):
        db.drop_collection(f"{current}_previous")
        if current in db.list_collection_names():
            db[current].rename(f"{current}_previous", dropTarget=True)
        db[replacement].rename(current, dropTarget=True)
    return {"records": total, "first_date": first, "last_date": last, "months": len(months), "min_month": min(counts), "max_month": max(counts)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye e intercambia un histórico analítico continuo.")
    parser.add_argument("--count", type=int, default=2_000_000)
    parser.add_argument("--end-date", default=DEFAULT_END.isoformat())
    parser.add_argument("--seed", type=int, default=20260824)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count debe ser positivo")
    end = date.fromisoformat(args.end_date)
    uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    db_name = os.getenv("MONGO_DB", "globtrade_dw")
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    try:
        report = build_dataset(client[db_name], total=args.count, end=end, seed=args.seed)
        print(report, flush=True)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
