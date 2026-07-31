# -*- coding: utf-8 -*-
"""Informes compuestos RC-01…RC-08 (agregaciones / ELT / estrella)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from shared.data_layers import analytics_fact, strategic_ready
from shared.mongo import get_db

COMPLEX_REPORTS: list[dict[str, Any]] = [
    {
        "id": "RC-01",
        "name": "Ventas por mes y por categoría de producto",
        "objetivo": "OT1, OT7, OT10, OT12",
        "para_que": "Ver cómo evolucionan las ventas por categoría en el tiempo.",
        "quien": "Gerente general, analista",
        "columns": ["mes", "categoria", "pedidos", "unidades", "ingresos", "utilidad"],
    },
    {
        "id": "RC-02",
        "name": "Top 10 productos que más se venden y top 10 que menos se venden",
        "objetivo": "OT7, OT10, OT12",
        "para_que": "Comparar categorías/productos líderes y rezagados por ingresos.",
        "quien": "Gerente comercial, analista",
        "columns": ["ranking", "categoria", "pedidos", "unidades", "ingresos", "grupo"],
    },
    {
        "id": "RC-03",
        "name": "Balanza interna: cuánto se vendió frente a cuánto se compró",
        "objetivo": "OT4",
        "para_que": "Comparar ventas frente a compras recibidas en el mismo periodo.",
        "quien": "Jefe de compras, gerencia",
        "columns": ["concepto", "monto", "detalle"],
    },
    {
        "id": "RC-04",
        "name": "Qué tan rápido rota el inventario por categoría",
        "objetivo": "OT3",
        "para_que": "Cruzar unidades vendidas con stock actual por categoría.",
        "quien": "Jefe de inventario",
        "columns": ["categoria", "unidades_vendidas", "stock_actual", "rotacion_aprox"],
    },
    {
        "id": "RC-05",
        "name": "Tiempo promedio entre pedir y enviar, por país o región",
        "objetivo": "OT5",
        "para_que": "Medir demora logística promedio por región.",
        "quien": "Jefe de logística",
        "columns": ["region", "pedidos", "dias_promedio"],
    },
    {
        "id": "RC-06",
        "name": "Cuánto se usan los cupones y cómo afectan las ventas",
        "objetivo": "OT6, OT9",
        "para_que": "Medir uso de cupones e impacto en ingresos del periodo.",
        "quien": "Gerente comercial",
        "columns": ["cupon", "usos_landing", "ingresos_con_cupon", "descuento_total", "activo"],
    },
    {
        "id": "RC-07",
        "name": "Ganancia (margen) por categoría de producto en el tiempo",
        "objetivo": "OT2, OT12",
        "para_que": "Ver margen % por categoría y mes.",
        "quien": "Gerente, analista",
        "columns": ["mes", "categoria", "ingresos", "costos", "utilidad", "margen_pct"],
    },
    {
        "id": "RC-08",
        "name": "Estado de la carga de datos para informes",
        "objetivo": "OT11, OT12",
        "para_que": "Verificar si los datos de ventas están listos para análisis.",
        "quien": "Administrador, analista",
        "columns": ["indicador", "valor", "estado"],
    },
]

COMPLEX_BY_ID = {r["id"]: r for r in COMPLEX_REPORTS}


def list_complex_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "objetivo": r["objetivo"],
            "para_que": r["para_que"],
            "quien": r["quien"],
            "tipo": "compuesto",
            "columns": r["columns"],
            "data_layer": "estrategico",
        }
        for r in COMPLEX_REPORTS
    ]


def _cat_lookup_pipe(local: str = "category_id") -> list[dict[str, Any]]:
    return [
        {
            "$lookup": {
                "from": "dim_categoria",
                "localField": local,
                "foreignField": "category_id",
                "as": "_cat",
            }
        },
        {"$addFields": {"categoria": {"$ifNull": [{"$arrayElemAt": ["$_cat.name", 0]}, "Sin categoría"]}}},
        {"$project": {"_cat": 0}},
    ]


def rc01(*, limit: int = 200) -> dict[str, Any]:
    if not strategic_ready():
        return {"rows": [], "total": 0, "message": "fact_ventas vacío — ejecuta Construir modelo."}
    pipe = [
        {
            "$group": {
                "_id": {"mes": {"$substr": ["$fecha_id", 0, 7]}, "category_id": "$category_id"},
                "pedidos": {"$sum": 1},
                "unidades": {"$sum": "$units_sold"},
                "ingresos": {"$sum": "$total_revenue"},
                "utilidad": {"$sum": "$total_profit"},
            }
        },
        {"$sort": {"_id.mes": -1, "ingresos": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "dim_categoria",
                "localField": "_id.category_id",
                "foreignField": "category_id",
                "as": "_cat",
            }
        },
        {
            "$project": {
                "_id": 0,
                "mes": "$_id.mes",
                "categoria": {"$ifNull": [{"$arrayElemAt": ["$_cat.name", 0]}, "—"]},
                "pedidos": 1,
                "unidades": 1,
                "ingresos": {"$round": ["$ingresos", 2]},
                "utilidad": {"$round": ["$utilidad", 2]},
            }
        },
    ]
    rows = list(analytics_fact().aggregate(pipe, allowDiskUse=True))
    return {"rows": rows, "total": len(rows)}


def rc02(*, limit: int = 10) -> dict[str, Any]:
    if not strategic_ready():
        return {"rows": [], "total": 0, "message": "fact_ventas vacío."}
    base = [
        {
            "$group": {
                "_id": "$category_id",
                "pedidos": {"$sum": 1},
                "unidades": {"$sum": "$units_sold"},
                "ingresos": {"$sum": "$total_revenue"},
            }
        },
        {
            "$lookup": {
                "from": "dim_categoria",
                "localField": "_id",
                "foreignField": "category_id",
                "as": "_cat",
            }
        },
        {
            "$project": {
                "categoria": {"$ifNull": [{"$arrayElemAt": ["$_cat.name", 0]}, "—"]},
                "pedidos": 1,
                "unidades": 1,
                "ingresos": {"$round": ["$ingresos", 2]},
            }
        },
    ]
    top = list(
        analytics_fact().aggregate(
            base + [{"$sort": {"ingresos": -1}}, {"$limit": limit}],
            allowDiskUse=True,
        )
    )
    bottom = list(
        analytics_fact().aggregate(
            base + [{"$sort": {"ingresos": 1}}, {"$limit": limit}],
            allowDiskUse=True,
        )
    )
    rows = []
    for i, r in enumerate(top, 1):
        rows.append(
            {
                "ranking": i,
                "categoria": r.get("categoria"),
                "pedidos": r.get("pedidos"),
                "unidades": r.get("unidades"),
                "ingresos": r.get("ingresos"),
                "grupo": "Top ventas",
            }
        )
    for i, r in enumerate(bottom, 1):
        rows.append(
            {
                "ranking": i,
                "categoria": r.get("categoria"),
                "pedidos": r.get("pedidos"),
                "unidades": r.get("unidades"),
                "ingresos": r.get("ingresos"),
                "grupo": "Menor ventas",
            }
        )
    return {"rows": rows, "total": len(rows)}


def rc03(*, limit: int = 20) -> dict[str, Any]:
    db = get_db()
    ventas = 0.0
    if strategic_ready():
        agg = list(
            analytics_fact().aggregate(
                [{"$group": {"_id": None, "r": {"$sum": "$total_revenue"}}}],
                allowDiskUse=True,
            )
        )
        ventas = float((agg[0]["r"] if agg else 0) or 0)
    compras = 0.0
    for po in db["purchase_orders"].find(
        {"status": {"$in": ["recibida", "parcial", "enviada"]}},
        {"_id": 0, "total": 1, "lines": 1},
    ):
        if po.get("total") is not None:
            compras += float(po.get("total") or 0)
        else:
            for ln in po.get("lines") or []:
                compras += float(ln.get("quantity_ordered") or 0) * float(ln.get("unit_cost") or 0)
    rows = [
        {"concepto": "Ventas (fact_ventas ingresos)", "monto": round(ventas, 2), "detalle": "Capa estratégica"},
        {
            "concepto": "Compras (OC enviada/parcial/recibida)",
            "monto": round(compras, 2),
            "detalle": "Capa operativa",
        },
        {
            "concepto": "Balanza (ventas − compras)",
            "monto": round(ventas - compras, 2),
            "detalle": "Positivo = más vendido que comprado (aprox.)",
        },
    ]
    return {"rows": rows[:limit], "total": len(rows)}


def rc04(*, limit: int = 50) -> dict[str, Any]:
    db = get_db()
    sold: dict[str, float] = {}
    if strategic_ready():
        for r in analytics_fact().aggregate(
            [
                {"$group": {"_id": "$category_id", "u": {"$sum": "$units_sold"}}},
                {
                    "$lookup": {
                        "from": "dim_categoria",
                        "localField": "_id",
                        "foreignField": "category_id",
                        "as": "_cat",
                    }
                },
                {
                    "$project": {
                        "categoria": {"$ifNull": [{"$arrayElemAt": ["$_cat.name", 0]}, "—"]},
                        "u": 1,
                    }
                },
            ],
            allowDiskUse=True,
        ):
            sold[r.get("categoria") or "—"] = float(r.get("u") or 0)

    stock: dict[str, float] = {}
    for v in db["product_variants"].find({}, {"_id": 0, "product_id": 1, "inventory_quantity": 1}):
        p = db["products"].find_one({"product_id": v.get("product_id")}, {"_id": 0, "product_id": 1})
        cat = "—"
        if p:
            link = db["collection_products"].find_one({"product_id": p.get("product_id")}, {"_id": 0})
            if link:
                col = db["collections"].find_one(
                    {"collection_id": link.get("collection_id")}, {"_id": 0, "title": 1}
                )
                cat = (col or {}).get("title") or "—"
        stock[cat] = stock.get(cat, 0) + float(v.get("inventory_quantity") or 0)

    cats = sorted(set(sold) | set(stock))
    rows = []
    for c in cats:
        u = sold.get(c, 0)
        s = stock.get(c, 0)
        rot = round(u / s, 2) if s else None
        rows.append(
            {
                "categoria": c,
                "unidades_vendidas": int(u),
                "stock_actual": int(s),
                "rotacion_aprox": rot if rot is not None else "Sin stock",
            }
        )
    rows.sort(key=lambda x: float(x["rotacion_aprox"]) if isinstance(x["rotacion_aprox"], (int, float)) else -1, reverse=True)
    return {"rows": rows[:limit], "total": len(rows)}


def rc05(*, limit: int = 50) -> dict[str, Any]:
    db = get_db()
    rows_out: list[dict[str, Any]] = []
    pipe = [
        {
            "$match": {
                "shipped_at": {"$nin": [None, ""]},
                "created_at": {"$nin": [None, ""]},
            }
        },
        {"$project": {"country_id": 1, "created_at": 1, "shipped_at": 1}},
    ]
    by_region: dict[str, list[float]] = {}
    for r in db["purchase_requests"].aggregate(pipe):
        try:
            c0 = str(r.get("created_at"))[:10]
            s0 = str(r.get("shipped_at"))[:10]
            d0 = datetime.fromisoformat(c0)
            d1 = datetime.fromisoformat(s0)
            days = (d1 - d0).days
        except Exception:
            continue
        country = db["dim_pais"].find_one({"country_id": r.get("country_id")}, {"_id": 0})
        region = "—"
        if country:
            reg = db["dim_region"].find_one({"region_id": country.get("region_id")}, {"_id": 0, "name": 1})
            region = (reg or {}).get("name") or "—"
        by_region.setdefault(region, []).append(float(days))
    for region, vals in sorted(by_region.items()):
        rows_out.append(
            {
                "region": region,
                "pedidos": len(vals),
                "dias_promedio": round(sum(vals) / len(vals), 1) if vals else 0,
            }
        )
    rows_out.sort(key=lambda x: x["dias_promedio"], reverse=True)
    return {"rows": rows_out[:limit], "total": len(rows_out)}


def rc06(*, limit: int = 50) -> dict[str, Any]:
    db = get_db()
    codes = {c.get("code"): c for c in db["discount_codes"].find({}, {"_id": 0})}
    agg = list(
        db["sales_records"].aggregate(
            [
                {"$match": {"discount_code": {"$nin": [None, ""]}}},
                {
                    "$group": {
                        "_id": "$discount_code",
                        "usos": {"$sum": 1},
                        "ingresos": {"$sum": "$total_revenue"},
                        "descuento": {"$sum": {"$ifNull": ["$discount_alloc", 0]}},
                    }
                },
                {"$sort": {"usos": -1}},
                {"$limit": limit},
            ],
            allowDiskUse=True,
        )
    )
    rows = []
    for a in agg:
        code = a.get("_id")
        meta = codes.get(code) or {}
        rows.append(
            {
                "cupon": code,
                "usos_landing": a.get("usos"),
                "ingresos_con_cupon": round(float(a.get("ingresos") or 0), 2),
                "descuento_total": round(float(a.get("descuento") or 0), 2),
                "activo": bool(meta.get("active", True)) if meta else "—",
            }
        )
    if not rows:
        for code, meta in list(codes.items())[:limit]:
            rows.append(
                {
                    "cupon": code,
                    "usos_landing": meta.get("uses") or meta.get("used_count") or 0,
                    "ingresos_con_cupon": 0,
                    "descuento_total": 0,
                    "activo": bool(meta.get("active", True)),
                }
            )
    return {"rows": rows, "total": len(rows)}


def rc07(*, limit: int = 200) -> dict[str, Any]:
    if not strategic_ready():
        return {"rows": [], "total": 0, "message": "fact_ventas vacío."}
    pipe = [
        {
            "$group": {
                "_id": {"mes": {"$substr": ["$fecha_id", 0, 7]}, "category_id": "$category_id"},
                "ingresos": {"$sum": "$total_revenue"},
                "costos": {"$sum": "$total_cost"},
                "utilidad": {"$sum": "$total_profit"},
            }
        },
        {"$sort": {"_id.mes": -1, "utilidad": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "dim_categoria",
                "localField": "_id.category_id",
                "foreignField": "category_id",
                "as": "_cat",
            }
        },
        {
            "$project": {
                "_id": 0,
                "mes": "$_id.mes",
                "categoria": {"$ifNull": [{"$arrayElemAt": ["$_cat.name", 0]}, "—"]},
                "ingresos": {"$round": ["$ingresos", 2]},
                "costos": {"$round": ["$costos", 2]},
                "utilidad": {"$round": ["$utilidad", 2]},
                "margen_pct": {
                    "$cond": [
                        {"$gt": ["$ingresos", 0]},
                        {"$round": [{"$multiply": [{"$divide": ["$utilidad", "$ingresos"]}, 100]}, 2]},
                        0,
                    ]
                },
            }
        },
    ]
    rows = list(analytics_fact().aggregate(pipe, allowDiskUse=True))
    return {"rows": rows, "total": len(rows)}


def rc08(*, limit: int = 20) -> dict[str, Any]:
    db = get_db()
    landing = db["sales_records"].estimated_document_count()
    fact = db["fact_ventas"].estimated_document_count()
    ready = strategic_ready()
    lag = False
    try:
        from shared.analytics_sync import get_strategic_lag

        lag = bool(get_strategic_lag().get("strategic_lagging"))
    except Exception:
        pass
    last_build = None
    try:
        from shared.data_layers import layers_overview

        last_build = layers_overview().get("last_build")
    except Exception:
        pass
    rows = [
        {
            "indicador": "sales_records (landing)",
            "valor": f"{landing:,}",
            "estado": "OK" if landing else "Vacío",
        },
        {
            "indicador": "fact_ventas (estratégico)",
            "valor": f"{fact:,}",
            "estado": "OK" if ready else "Vacío — Construir modelo",
        },
        {
            "indicador": "Alineación landing ↔ fact",
            "valor": f"Δ docs ≈ {landing - fact:,}",
            "estado": "Desfasado" if lag or (landing and not fact) else "Alineado / aceptable",
        },
        {
            "indicador": "Último build_model / ELT",
            "valor": last_build or "—",
            "estado": "Registrado" if last_build else "Sin auditoría de build",
        },
        {
            "indicador": "strategic_ready",
            "valor": str(ready),
            "estado": "Listo para Tablero" if ready else "Bloqueado",
        },
    ]
    return {"rows": rows[:limit], "total": len(rows)}


_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "RC-01": rc01,
    "RC-02": rc02,
    "RC-03": rc03,
    "RC-04": rc04,
    "RC-05": rc05,
    "RC-06": rc06,
    "RC-07": rc07,
    "RC-08": rc08,
}


def run_complex_report(report_id: str, *, limit: int = 100) -> dict[str, Any]:
    rid = (report_id or "").strip().upper()
    meta = COMPLEX_BY_ID.get(rid)
    if not meta:
        raise ValueError("unknown_report")
    data = _RUNNERS[rid](limit=limit)
    return {
        "report": {
            "id": meta["id"],
            "name": meta["name"],
            "objetivo": meta["objetivo"],
            "para_que": meta["para_que"],
            "quien": meta["quien"],
            "tipo": "compuesto",
            "columns": meta["columns"],
            "data_layer": "estrategico",
        },
        **data,
    }
