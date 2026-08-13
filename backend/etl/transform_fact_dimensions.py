"""Paso 4 — Dimensiones, hechos y espejos SQL (sin duplicar products / product_categories)."""
from __future__ import annotations

import os
import sys
from datetime import datetime

import pandas as pd
from pymongo import MongoClient

from shared.collections_q1 import drop_duplicate_catalog_collections

CATEGORY_DESC = {
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


def _mirror(db, src: str, dst: str) -> None:
    docs = list(db[src].find({}, {"_id": 0}))
    db[dst].delete_many({})
    if docs:
        db[dst].insert_many(docs)
    print(f"  {dst}: {len(docs)}")


def main(mongo_uri: str | None = None, mongo_db: str | None = None) -> None:
    uri = mongo_uri or os.getenv("MONGO_URI")
    name = mongo_db or os.getenv("MONGO_DB")
    if not uri or not name:
        try:
            from config.settings import settings as _s

            uri = uri or _s.mongo_uri
            name = name or _s.mongo_db
        except ImportError:
            uri = uri or "mongodb://localhost:27017"
            name = name or "globtrade_dw"

    client = MongoClient(uri)
    db = client[name]
    rows = list(db["sales_records"].find({}, {"_id": 0}))
    if not rows:
        print("sales_records vacío.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(rows)
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

    from paquetes.tablero import catalogo_modelo as cat_model
    from paquetes.tablero import catalogo_nombres as nom

    # ── Regiones y países ─────────────────────────────────────────────
    db["dim_region"].delete_many({})
    rmap: dict[str, int] = {}
    regions = []
    for i, rname in enumerate(sorted(df["region"].dropna().unique()), start=1):
        regions.append({"region_id": i, "name": rname, "description": f"Zona comercial: {rname}"})
        rmap[rname] = i
    db["dim_region"].insert_many(regions)

    db["dim_pais"].delete_many({})
    cmap: dict[str, int] = {}
    paises = []
    for i, row in enumerate(
        df[["country", "region"]].drop_duplicates().sort_values("country").itertuples(index=False),
        start=1,
    ):
        paises.append({"country_id": i, "name": row.country, "region_id": rmap[row.region]})
        cmap[row.country] = i
    db["dim_pais"].insert_many(paises)

    # ── Categorías y productos (catálogo oficial 120 SKUs) ───────────
    catmap = {nom.CATEGORY_BY_ID[cid]: cid for cid in nom.CATEGORY_BY_ID}
    db["dim_categoria"].delete_many({})
    categorias = []
    for cid in sorted(nom.CATEGORY_BY_ID.keys()):
        cname = nom.CATEGORY_BY_ID[cid]
        categorias.append(
            {
                "category_id": cid,
                "name": cname,
                "description": CATEGORY_DESC.get(cname, "Categoría general"),
            }
        )
    db["dim_categoria"].insert_many(categorias)

    old_images = {
        int(r["product_id"]): r.get("image_url")
        for r in db["dim_producto"].find({"image_url": {"$ne": None}}, {"product_id": 1, "image_url": 1})
    }
    productos = []
    for cid in sorted(nom.CATEGORY_BY_ID.keys()):
        cname = nom.CATEGORY_BY_ID[cid]
        sub = df[df["item_type"] == cname]
        if sub.empty:
            continue
        stats = {
            "revenue": float(sub["total_revenue"].sum()),
            "units": int(sub["units_sold"].sum()),
            "orders": len(sub),
            "unit_price": float(sub["unit_price"].iloc[0]),
            "unit_cost": float(sub["unit_cost"].mean()),
        }
        for p in cat_model.build_products_for_category(cid, cname, stats):
            pid = int(p["product_id"])
            productos.append(
                {
                    "product_id": pid,
                    "name": p["name"],
                    "category_id": int(p["category_id"]),
                    "line": int(p["line"]),
                    "unit_price": p["unit_price"],
                    "unit_cost": p["unit_cost"],
                    "margin_pct": p["margin_pct"],
                    "units": p["units"],
                    "orders": p["orders"],
                    "revenue": p["revenue"],
                    "image_url": old_images.get(pid),
                }
            )
    db["dim_producto"].delete_many({})
    if productos:
        db["dim_producto"].insert_many(productos)

    # ── Canal y prioridad ───────────────────────────────────────────
    db["dim_canal"].delete_many({})
    chmap = {"Online": 1, "Offline": 2}
    db["dim_canal"].insert_many(
        [
            {"channel_id": 1, "name": "Online", "description": "Ventas digitales"},
            {"channel_id": 2, "name": "Offline", "description": "Ventas físicas"},
        ]
    )

    db["dim_prioridad"].delete_many({})
    pmap = {"C": 1, "H": 2, "M": 3, "L": 4}
    db["dim_prioridad"].insert_many(
        [
            {"priority_id": 1, "code": "C", "name": "Critical", "sla_days": 1, "description": "24h"},
            {"priority_id": 2, "code": "H", "name": "High", "sla_days": 3, "description": "3 días"},
            {"priority_id": 3, "code": "M", "name": "Medium", "sla_days": 7, "description": "7 días"},
            {"priority_id": 4, "code": "L", "name": "Low", "sla_days": 15, "description": "15 días"},
        ]
    )

    # ── Clientes y tiempo ─────────────────────────────────────────────
    db["dim_cliente"].delete_many({})
    client_lookup: dict[tuple, int] = {}
    clientes = []
    for i, row in enumerate(df[["country", "sales_channel"]].drop_duplicates().itertuples(index=False), start=1):
        client_lookup[(row.country, row.sales_channel)] = i
        clientes.append(
            {
                "client_id": i,
                "name": f"Cliente-{i:05d}",
                "country_id": cmap[row.country],
                "channel_id": chmap.get(row.sales_channel, 1),
                "email": None,
                "phone": None,
                "created_at": datetime.now().date().isoformat(),
            }
        )
    db["dim_cliente"].insert_many(clientes)

    db["dim_tiempo"].delete_many({})
    tiempos = []
    tmap: dict[str, int] = {}
    for i, fecha in enumerate(sorted(df["order_date"].dropna().dt.date.unique()), start=1):
        tiempos.append(
            {
                "tiempo_id": i,
                "fecha_id": fecha.isoformat(),
                "anio": fecha.year,
                "mes": fecha.month,
                "trimestre": (fecha.month - 1) // 3 + 1,
            }
        )
        tmap[fecha.isoformat()] = i
    db["dim_tiempo"].insert_many(tiempos)

    # ── Hechos y pedidos (vectorizado + insert por lotes) ─────────────
    db["fact_ventas"].delete_many({})
    db["order_lines"].delete_many({})
    db["orders"].delete_many({})

    work = df.copy()
    work["venta_id"] = range(1, len(work) + 1)
    work["order_id"] = work["order_id"].astype(str)
    work["fecha_id"] = work["order_date"].dt.strftime("%Y-%m-%d")
    work["tiempo_id"] = work["fecha_id"].map(tmap)
    work["region_id"] = work["region"].map(rmap)
    work["country_id"] = work["country"].map(cmap)
    work["category_id"] = work["item_type"].map(catmap)
    work["channel_id"] = work["sales_channel"].map(chmap)
    work["priority_id"] = work["order_priority"].map(pmap)
    work["client_id"] = work.apply(
        lambda r: client_lookup.get((r["country"], r["sales_channel"])), axis=1
    )
    work["line_revenue"] = (work["units_sold"] * work["unit_price"]).round(2)
    work["line_cost"] = (work["units_sold"] * work["unit_cost"]).round(2)
    work["line_profit"] = (work["units_sold"] * (work["unit_price"] - work["unit_cost"])).round(2)

    fact_cols = [
        "venta_id", "order_id", "tiempo_id", "fecha_id", "region_id", "country_id",
        "category_id", "channel_id", "priority_id", "client_id", "units_sold",
        "unit_price", "unit_cost", "total_revenue", "total_cost", "total_profit",
        "line_revenue", "line_cost", "line_profit",
    ]
    work["line_id"] = work["venta_id"]
    work["order_id_key"] = work["order_id"].map(
        lambda x: int(x) if str(x).isdigit() else str(x)
    )
    work["order_date_str"] = work["order_date"].dt.strftime("%Y-%m-%d")
    work["ship_date_str"] = work["ship_date"].dt.strftime("%Y-%m-%d")
    work["delivery_days"] = (work["ship_date"] - work["order_date"]).dt.days

    insert_batch = 25_000
    total_rows = len(work)
    for start in range(0, total_rows, insert_batch):
        chunk = work.iloc[start : start + insert_batch]
        facts = chunk[fact_cols].to_dict(orient="records")
        lines = chunk.rename(columns={"order_id_key": "order_id"})[
            ["line_id", "order_id", "category_id", "units_sold", "unit_price", "unit_cost",
             "line_revenue", "line_cost", "line_profit"]
        ].to_dict(orient="records")
        orders = chunk.rename(columns={"order_id_key": "order_id"})[
            ["order_id", "client_id", "country_id", "channel_id", "priority_id",
             "order_date_str", "ship_date_str", "delivery_days",
             "total_revenue", "total_cost", "total_profit"]
        ].rename(columns={"order_date_str": "order_date", "ship_date_str": "ship_date"}).to_dict(orient="records")
        for row in orders:
            row["status"] = "Delivered"
        db["fact_ventas"].insert_many(facts, ordered=False)
        db["order_lines"].insert_many(lines, ordered=False)
        db["orders"].insert_many(orders, ordered=False)
        done = min(start + insert_batch, total_rows)
        if done % 100_000 == 0 or done == total_rows:
            print(f"  fact_ventas {done:,}/{total_rows:,}")

    db["monthly_kpis"].delete_many({})
    df["year"] = df["order_date"].dt.year
    df["month"] = df["order_date"].dt.month
    kpis = []
    for kid, (keys, g) in enumerate(df.groupby(["year", "month", "region", "item_type"], dropna=False), start=1):
        rev, prof = g["total_revenue"].sum(), g["total_profit"].sum()
        kpis.append(
            {
                "kpi_id": kid,
                "year": int(keys[0]) if pd.notna(keys[0]) else None,
                "month": int(keys[1]) if pd.notna(keys[1]) else None,
                "region": keys[2],
                "item_type": keys[3],
                "total_orders": len(g),
                "total_units": int(g["units_sold"].sum()),
                "total_revenue": round(float(rev), 2),
                "total_cost": round(float(g["total_cost"].sum()), 2),
                "total_profit": round(float(prof), 2),
                "avg_margin_pct": round(float((prof / rev * 100) if rev else 0), 2),
            }
        )
    if kpis:
        db["monthly_kpis"].insert_many(kpis)

    print("Espejos SQL (sin products ni product_categories):")
    _mirror(db, "dim_region", "regions")
    _mirror(db, "dim_pais", "countries")
    _mirror(db, "dim_canal", "sales_channels")
    _mirror(db, "dim_prioridad", "order_priorities")
    _mirror(db, "dim_cliente", "clients")

    print("Eliminando duplicados de catálogo…")
    for dropped in drop_duplicate_catalog_collections(db):
        print(f"  eliminada: {dropped}")

    print(f"  sales_records: {db['sales_records'].count_documents({})}")
    print(f"  dim_producto: {db['dim_producto'].count_documents({})}")
    print(f"  fact_ventas: {db['fact_ventas'].count_documents({})}")
    client.close()


if __name__ == "__main__":
    main()
