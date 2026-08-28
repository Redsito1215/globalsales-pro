"""Servicios de decisiones de negocio — margen (estratégico), stock y embudo (operativo)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import ceil, sqrt
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic

from shared.data_layers import analytics_fact, strategic_ready
from shared.mongo import get_db
from shared.clickhouse import ensure_database_and_schema, ping_clickhouse, query_rows

_PANEL_CACHE: dict[tuple[int, int, int], tuple[float, dict[str, Any]]] = {}
_PANEL_CACHE_LOCK = Lock()
_PANEL_CACHE_TTL = 90.0


def _forecast_values(values: list[float], periods: int = 3) -> dict[str, Any]:
    """Pronóstico explicable: promedio ponderado reciente + tendencia amortiguada."""
    clean = [max(float(value or 0), 0.0) for value in values]
    periods = max(1, min(int(periods), 6))
    if len(clean) < 3:
        return {"forecast": [], "confidence": "insuficiente", "confidence_pct": 0, "trend_pct": 0}
    recent = clean[-3:]
    base = sum(value * weight for value, weight in zip(recent, (0.2, 0.3, 0.5)))
    previous = clean[-6:-3]
    trend = (sum(recent) / len(recent) - sum(previous) / len(previous)) / 3 if previous else 0.0
    trend = max(-base * 0.25, min(trend, base * 0.25))
    forecast = [round(max(base + trend * step, 0), 2) for step in range(1, periods + 1)]
    mean = sum(clean) / len(clean)
    variance = sum((value - mean) ** 2 for value in clean) / len(clean)
    cv = sqrt(variance) / mean if mean else 1.0
    confidence_pct = round(max(20, min(92, 92 - cv * 45 - max(0, 6 - len(clean)) * 7)))
    confidence = "alta" if confidence_pct >= 75 else "media" if confidence_pct >= 50 else "baja"
    recent_avg = sum(recent) / len(recent)
    previous_avg = sum(previous) / len(previous) if previous else recent_avg
    trend_pct = round((recent_avg - previous_avg) / previous_avg * 100, 1) if previous_avg else 0.0
    return {"forecast": forecast, "confidence": confidence, "confidence_pct": confidence_pct, "trend_pct": trend_pct}


def demand_forecast(*, months: int = 12, horizon: int = 3, limit: int = 12) -> dict[str, Any]:
    """Pronóstico mensual por producto usando el último mes disponible en ClickHouse."""
    months = max(6, min(int(months), 24))
    horizon = max(1, min(int(horizon), 6))
    limit = max(3, min(int(limit), 50))
    if not ping_clickhouse():
        return {"ready": False, "items": [], "summary": {}, "source": "clickhouse",
                "message": "ClickHouse no está disponible. Publica el modelo estratégico para calcular el pronóstico."}
    rows = query_rows(
        """
        WITH (SELECT max(sale_date) FROM fact_sales) AS anchor
        SELECT product_id, any(product) product, any(category) category,
               toStartOfMonth(sale_date) month, round(sum(units),2) units
        FROM fact_sales
        WHERE sale_date >= addMonths(toStartOfMonth(anchor), -{months:UInt16}) AND product_id > 0
        GROUP BY product_id, month ORDER BY product_id, month
        """, {"months": months - 1},
    )
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        product_id = int(row.get("product_id") or 0)
        if not product_id:
            continue
        item = grouped.setdefault(product_id, {"product_id": product_id, "product": row.get("product"),
                                               "category": row.get("category"), "history": []})
        item["history"].append({"month": str(row.get("month"))[:10], "units": float(row.get("units") or 0)})
    inventory = {}
    for row in query_rows("SELECT product_id, round(sum(stock),2) stock FROM inventory_snapshot FINAL GROUP BY product_id"):
        pid, stock = int(row.get("product_id") or 0), float(row.get("stock") or 0)
        if pid:
            inventory[pid] = 100.0 if stock > 1_000_000 else stock
    items = []
    for product_id, item in grouped.items():
        calc = _forecast_values([point["units"] for point in item["history"]], horizon)
        if not calc["forecast"]:
            continue
        predicted = round(sum(calc["forecast"]), 2)
        stock = round(inventory.get(product_id, 0), 2)
        recommended = max(ceil(predicted * 1.10 - stock), 0)
        items.append({**item, **calc, "forecast_total": predicted, "stock": stock,
                      "recommended_purchase": recommended,
                      "decision": f"Comprar {recommended} unidades" if recommended else "Inventario suficiente para el horizonte"})
    items.sort(key=lambda row: (row["recommended_purchase"], row["forecast_total"]), reverse=True)
    return {"ready": True, "source": "clickhouse", "months": months, "horizon": horizon, "items": items[:limit],
            "summary": {"products": len(items), "forecast_units": round(sum(x["forecast_total"] for x in items), 2),
                        "purchase_units": sum(x["recommended_purchase"] for x in items),
                        "low_confidence": sum(x["confidence"] == "baja" for x in items)},
            "method": "Promedio móvil ponderado con tendencia amortiguada y 10% de reserva."}


def true_profitability(*, limit: int = 20) -> dict[str, Any]:
    """Rentabilidad neta: descuento, costo, envío, impuesto y devoluciones."""
    db = get_db()
    limit = max(5, min(int(limit), 100))
    requests = list(db["purchase_requests"].find(
        {"status": {"$in": ["convertida", "enviada", "entregada", "devuelta"]}}, {"_id": 0}
    ).sort("request_id", -1).limit(1000))
    request_ids = [int(row["request_id"]) for row in requests if row.get("request_id") is not None]
    lines_by_request: dict[int, list[dict[str, Any]]] = {}
    for line in db["purchase_request_lines"].find({"request_id": {"$in": request_ids}}, {"_id": 0}):
        lines_by_request.setdefault(int(line.get("request_id") or 0), []).append(line)
    refunds_by_request: dict[int, float] = {}
    for note in db["credit_notes"].find({"request_id": {"$in": request_ids}, "status": "issued"}, {"_id": 0}):
        rid = int(note.get("request_id") or 0)
        refunds_by_request[rid] = refunds_by_request.get(rid, 0.0) + float(note.get("amount") or 0)
    try:
        from shared.company_profile import get_company_profile
        tax_rate = float(get_company_profile().get("tax_rate") or 0)
    except (TypeError, ValueError):
        tax_rate = 0.0
    orders, products = [], {}
    for req in requests:
        rid = int(req.get("request_id") or 0)
        lines = lines_by_request.get(rid, [])
        line_revenue = [float(line.get("line_net") if line.get("line_net") is not None else
                              float(line.get("unit_price") or 0) * int(line.get("quantity") or 0)) for line in lines]
        merchandise_revenue = round(sum(line_revenue), 2)
        shipping = round(float(req.get("shipping_cost") or 0), 2)
        charged = round(float(req.get("total") if req.get("total") is not None else merchandise_revenue + shipping), 2)
        refund = round(refunds_by_request.get(rid, float(req.get("return_refund_amount") or 0)), 2)
        product_cost = round(sum(float(line.get("unit_cost") or 0) * int(line.get("quantity") or 0) for line in lines), 2)
        tax = round(max(charged - refund, 0) * tax_rate / (100 + tax_rate), 2) if tax_rate else 0.0
        net_revenue = round(charged - refund, 2)
        net_profit = round(net_revenue - product_cost - shipping - tax, 2)
        margin = round(net_profit / net_revenue * 100, 2) if net_revenue else 0.0
        estimated = any(line.get("unit_cost") is None for line in lines)
        orders.append({"request_id": rid, "order_id": req.get("order_id"), "client": req.get("client_name") or req.get("client_email"),
                       "status": req.get("status"), "charged": charged, "discount": round(float(req.get("discount_amount") or 0), 2),
                       "refund": refund, "product_cost": product_cost, "shipping_cost": shipping, "tax": tax,
                       "net_revenue": net_revenue, "net_profit": net_profit, "margin_pct": margin, "estimated": estimated})
        alloc_base = merchandise_revenue or 1.0
        for line, revenue in zip(lines, line_revenue):
            key = int(line.get("product_id") or 0)
            row = products.setdefault(key, {"product_id": key, "product": line.get("product_name") or f"Producto {key}",
                                            "revenue": 0.0, "cost": 0.0, "expenses": 0.0, "orders": set(), "estimated": False})
            share = revenue / alloc_base
            row["revenue"] += revenue - refund * share
            row["cost"] += float(line.get("unit_cost") or 0) * int(line.get("quantity") or 0)
            row["expenses"] += (shipping + tax) * share
            row["orders"].add(rid)
            row["estimated"] = row["estimated"] or line.get("unit_cost") is None
    product_rows = []
    for row in products.values():
        revenue, cost, expenses = round(row["revenue"], 2), round(row["cost"], 2), round(row["expenses"], 2)
        profit = round(revenue - cost - expenses, 2)
        product_rows.append({**row, "revenue": revenue, "cost": cost, "expenses": expenses, "profit": profit,
                             "margin_pct": round(profit / revenue * 100, 2) if revenue else 0.0, "orders": len(row["orders"])})
    product_rows.sort(key=lambda row: row["profit"])
    orders.sort(key=lambda row: row["net_profit"])
    total_revenue = round(sum(row["net_revenue"] for row in orders), 2)
    total_profit = round(sum(row["net_profit"] for row in orders), 2)
    return {"orders": orders[:limit], "products": product_rows[:limit], "summary": {
        "orders": len(orders), "net_revenue": total_revenue, "net_profit": total_profit,
        "net_margin_pct": round(total_profit / total_revenue * 100, 2) if total_revenue else 0.0,
        "loss_orders": sum(row["net_profit"] < 0 for row in orders), "loss_products": sum(row["profit"] < 0 for row in product_rows),
        "refunds": round(sum(row["refund"] for row in orders), 2)},
        "method": "Ingreso cobrado menos devoluciones, costo del producto, envío e impuesto incluido.", "tax_rate": tax_rate}


def product_portfolio(*, lookback_days: int = 90, limit: int = 20) -> dict[str, Any]:
    """Portafolio gerencial: rentabilidad, rotación, estancamiento y reposición."""
    lookback_days = max(30, min(int(lookback_days), 365))
    limit = max(5, min(int(limit), 100))
    if not ping_clickhouse():
        return {
            "items": [], "summary": {}, "recommendations": [], "ready": False,
            "data_layer": "estrategico", "source": "clickhouse",
            "message": "ClickHouse no está disponible. Ejecuta el DAG para publicar el portafolio estratégico.",
        }

    sales = query_rows(
        """
        SELECT product_id, product, category,
               uniqExact(order_id) orders, round(sum(units),2) units,
               round(sum(revenue),2) revenue, round(sum(cost),2) cost,
               round(sum(profit),2) profit,
               round(if(sum(revenue)>0,sum(profit)/sum(revenue)*100,0),2) margin_pct,
               max(sale_date) last_sale,
               round(sum(units)/{days:UInt32},3) avg_daily_units
        FROM fact_sales
        WHERE sale_date >= today() - {days:UInt32}
        GROUP BY product_id, product, category
        SETTINGS prefer_column_name_to_alias = 1
        """,
        {"days": lookback_days},
    )
    inventory = query_rows(
        """
        SELECT product_id, any(product) product, any(category) category,
               round(sum(stock),2) stock, round(sum(inventory_value),2) inventory_value
        FROM inventory_snapshot FINAL GROUP BY product_id
        """
    )
    sales_by_id = {int(row.get("product_id") or 0): row for row in sales if int(row.get("product_id") or 0) > 0}
    inventory_by_id, invalid_inventory = {}, 0
    for row in inventory:
        pid = int(row.get("product_id") or 0)
        if pid <= 0:
            continue
        stock = float(row.get("stock") or 0)
        if stock > 1_000_000:
            unit_cost = float(row.get("inventory_value") or 0) / stock if stock else 0
            row = {**row, "stock": 100.0, "inventory_value": round(unit_cost * 100, 2), "stock_estimated": True}
            invalid_inventory += 1
        inventory_by_id[pid] = row
    product_ids = sorted(set(sales_by_id) | set(inventory_by_id))

    # Históricos sin product_id se muestran, pero se identifican como agregados por categoría.
    legacy_sales = [row for row in sales if int(row.get("product_id") or 0) == 0]
    revenues = sorted(float(row.get("revenue") or 0) for row in sales if float(row.get("revenue") or 0) > 0)
    revenue_median = revenues[len(revenues) // 2] if revenues else 0.0
    today = date.today()
    items: list[dict[str, Any]] = []

    for product_id in product_ids:
        sold = sales_by_id.get(product_id, {})
        inv = inventory_by_id.get(product_id, {})
        revenue = float(sold.get("revenue") or 0)
        margin = float(sold.get("margin_pct") or 0)
        stock = float(inv.get("stock") or 0)
        velocity = float(sold.get("avg_daily_units") or 0)
        last_sale_raw = sold.get("last_sale")
        if isinstance(last_sale_raw, datetime):
            last_sale = last_sale_raw.date()
        elif isinstance(last_sale_raw, date):
            last_sale = last_sale_raw
        else:
            try:
                last_sale = date.fromisoformat(str(last_sale_raw)[:10])
            except ValueError:
                last_sale = None
        days_without_sale = (today - last_sale).days if last_sale else None
        coverage_days = round(stock / velocity, 1) if velocity > 0 else None
        target_stock = ceil(velocity * 21)  # 14 días de entrega + 7 de seguridad.
        reorder_qty = max(target_stock - ceil(stock), 0) if velocity > 0 and (coverage_days or 0) < 14 else 0
        if revenue >= revenue_median and margin >= 20:
            quadrant = "Estrella"
            decision = "Proteger disponibilidad y mantener inversión comercial."
        elif revenue < revenue_median and margin >= 20:
            quadrant = "Oportunidad"
            decision = "Impulsar visibilidad antes de modificar el precio."
        elif revenue >= revenue_median and margin < 20:
            quadrant = "Volumen con margen débil"
            decision = "Revisar precio, descuento o costo del proveedor."
        else:
            quadrant = "Revisar portafolio"
            decision = "Reducir compra; liquidar si continúa sin movimiento."
        if days_without_sale is None and stock > 0:
            decision = "Sin ventas registradas: detener reposición y revisar liquidación."
        elif days_without_sale is not None and days_without_sale >= 60 and stock > 0:
            decision = f"Lleva {days_without_sale} días sin venderse: liquidar o reubicar inventario."
        if reorder_qty > 0:
            decision = f"Reponer {reorder_qty} unidades para recuperar al menos 21 días objetivo."
        items.append({
            "product_id": product_id, "product": sold.get("product") or inv.get("product") or f"Producto {product_id}",
            "category": sold.get("category") or inv.get("category") or "Sin categoría",
            "orders": int(sold.get("orders") or 0), "units": float(sold.get("units") or 0),
            "revenue": round(revenue, 2), "cost": round(float(sold.get("cost") or 0), 2),
            "profit": round(float(sold.get("profit") or 0), 2), "margin_pct": round(margin, 2),
            "stock": round(stock, 2), "inventory_value": round(float(inv.get("inventory_value") or 0), 2),
            "avg_daily_units": round(velocity, 3), "coverage_days": coverage_days,
            "days_without_sale": days_without_sale, "reorder_qty": reorder_qty,
            "quadrant": quadrant, "decision": decision, "stock_estimated": bool(inv.get("stock_estimated")),
        })

    priority = {"Estrella": 0, "Volumen con margen débil": 1, "Oportunidad": 2, "Revisar portafolio": 3}
    items.sort(key=lambda row: (0 if row["reorder_qty"] > 0 else 1, priority.get(row["quadrant"], 9), -row["revenue"]))
    summary = {
        "products": len(items),
        "stars": sum(row["quadrant"] == "Estrella" for row in items),
        "reorder_products": sum(row["reorder_qty"] > 0 for row in items),
        "reorder_units": sum(row["reorder_qty"] for row in items),
        "stagnant_products": sum((row["days_without_sale"] is None or row["days_without_sale"] >= 60) and row["stock"] > 0 for row in items),
        "capital_at_risk": round(sum(row["inventory_value"] for row in items if (row["days_without_sale"] is None or row["days_without_sale"] >= 60) and row["stock"] > 0), 2),
        "estimated_stock_products": invalid_inventory,
    }
    recommendations = []
    reorder = [row for row in items if row["reorder_qty"] > 0][:3]
    stagnant = [row for row in items if (row["days_without_sale"] is None or row["days_without_sale"] >= 60) and row["stock"] > 0][:3]
    weak = [row for row in items if row["quadrant"] == "Volumen con margen débil"][:3]
    if reorder:
        recommendations.append({"level": "danger", "title": "Reposición prioritaria", "detail": "; ".join(f"{r['product']}: {r['reorder_qty']} uds" for r in reorder), "action": "compras"})
    if stagnant:
        recommendations.append({"level": "warn", "title": "Capital inmovilizado", "detail": f"${summary['capital_at_risk']:,.2f} en productos sin movimiento suficiente. Revisa liquidación.", "action": "compras"})
    if weak:
        recommendations.append({"level": "info", "title": "Margen por corregir", "detail": "; ".join(f"{r['product']}: {r['margin_pct']}%" for r in weak), "action": "products"})
    if not recommendations:
        recommendations.append({"level": "ok", "title": "Portafolio estable", "detail": "No se detectaron decisiones urgentes con los datos publicados.", "action": "dashboard"})
    return {
        "items": items[:limit], "summary": summary, "recommendations": recommendations,
        "lookback_days": lookback_days, "ready": True, "data_layer": "estrategico",
        "source": "clickhouse", "granularity": "producto" if product_ids else "categoría histórica",
        "legacy_aggregates": len(legacy_sales),
    }


def product_margin_ranking(*, limit: int = 8) -> dict[str, Any]:
    """Top / bottom categorías por margen % — capa estratégica (fact_ventas)."""
    limit = max(3, min(int(limit), 20))
    if not strategic_ready():
        return {
            "top": [],
            "bottom": [],
            "total_categories": 0,
            "insight": "Capa estratégica vacía: ejecuta Carga ELT / Construir modelo.",
            "data_layer": "estrategico",
            "strategic_ready": False,
        }
    if ping_clickhouse():
        rows = query_rows("""
            SELECT category item_type, round(sum(revenue),2) revenue,
                   round(sum(profit),2) profit, round(sum(cost),2) cost,
                   uniqExact(order_id) orders, round(sum(units),2) units,
                   round(if(sum(revenue)>0,sum(profit)/sum(revenue)*100,0),1) margin_pct
            FROM fact_sales GROUP BY category HAVING sum(revenue) > 0
            ORDER BY margin_pct DESC, sum(profit) DESC
            SETTINGS prefer_column_name_to_alias = 1
        """)
    else:
        pipe = [
        {
            "$lookup": {
                "from": "dim_categoria",
                "localField": "category_id",
                "foreignField": "category_id",
                "as": "d",
            }
        },
        {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": {"$ifNull": ["$d.name", "Sin categoría"]},
                "revenue": {"$sum": "$total_revenue"},
                "profit": {"$sum": "$total_profit"},
                "cost": {"$sum": "$total_cost"},
                "orders": {"$sum": 1},
                "units": {"$sum": "$units_sold"},
            }
        },
        {"$match": {"revenue": {"$gt": 0}}},
        {
            "$project": {
                "_id": 0,
                "item_type": "$_id",
                "revenue": {"$round": ["$revenue", 2]},
                "profit": {"$round": ["$profit", 2]},
                "cost": {"$round": ["$cost", 2]},
                "orders": 1,
                "units": 1,
                "margin_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$profit", "$revenue"]}, 100]},
                        1,
                    ]
                },
            }
        },
        {"$sort": {"margin_pct": -1, "profit": -1}},
        ]
        rows = list(analytics_fact().aggregate(pipe, allowDiskUse=True))
    top = rows[:limit]
    bottom = list(reversed(rows[-limit:])) if len(rows) > limit else list(reversed(rows))
    if len(rows) <= limit:
        bottom = list(reversed(rows))

    insight = None
    if top and bottom:
        best = top[0]
        worst = bottom[0]
        insight = (
            f"Prioriza '{best['item_type']}' (margen {best.get('margin_pct')}%). "
            f"Revisa '{worst['item_type']}' (margen {worst.get('margin_pct')}%): "
            f"candidato a descontinuar, repricing o renegociar costo."
        )
    return {
        "top": top,
        "bottom": bottom,
        "total_categories": len(rows),
        "insight": insight,
        "data_layer": "estrategico",
        "strategic_ready": True,
    }


def channel_margin_ranking(*, limit: int = 6) -> list[dict[str, Any]]:
    if not strategic_ready():
        return []
    if ping_clickhouse():
        return query_rows("""
            SELECT channel, round(sum(revenue),2) revenue, round(sum(profit),2) profit,
                   uniqExact(order_id) orders,
                   round(if(sum(revenue)>0,sum(profit)/sum(revenue)*100,0),1) margin_pct
            FROM fact_sales GROUP BY channel HAVING sum(revenue) > 0
            ORDER BY margin_pct DESC LIMIT {limit:UInt16}
            SETTINGS prefer_column_name_to_alias = 1
        """, {"limit": max(2, min(int(limit), 12))})
    pipe = [
        {
            "$lookup": {
                "from": "dim_canal",
                "localField": "channel_id",
                "foreignField": "channel_id",
                "as": "d",
            }
        },
        {"$unwind": {"path": "$d", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": {"$ifNull": ["$d.name", "Sin canal"]},
                "revenue": {"$sum": "$total_revenue"},
                "profit": {"$sum": "$total_profit"},
                "orders": {"$sum": 1},
            }
        },
        {"$match": {"revenue": {"$gt": 0}}},
        {
            "$project": {
                "_id": 0,
                "channel": "$_id",
                "revenue": {"$round": ["$revenue", 2]},
                "profit": {"$round": ["$profit", 2]},
                "orders": 1,
                "margin_pct": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$profit", "$revenue"]}, 100]},
                        1,
                    ]
                },
            }
        },
        {"$sort": {"margin_pct": -1}},
        {"$limit": max(2, min(int(limit), 12))},
    ]
    return list(analytics_fact().aggregate(pipe, allowDiskUse=True))


def supplier_profitability(*, limit: int = 12) -> dict[str, Any]:
    """Rentabilidad estratégica por proveedor: utilidad de ventas frente a compras."""
    limit = max(5, min(int(limit), 50))
    if not ping_clickhouse():
        return {"ready": False, "items": [], "summary": {}, "source": "clickhouse",
                "message": "ClickHouse no está disponible para analizar proveedores."}
    ensure_database_and_schema()
    rows = query_rows("""
        WITH s AS (
          SELECT if(vendor='', 'Sin proveedor', vendor) proveedor,
                 uniqExact(order_id) pedidos, round(sum(units),2) unidades,
                 round(sum(revenue),2) ingresos, round(sum(cost),2) costos,
                 round(sum(profit),2) utilidad,
                 round(if(sum(revenue)>0,sum(profit)/sum(revenue)*100,0),2) margen_pct
          FROM fact_sales GROUP BY proveedor HAVING ingresos > 0
        ), p AS (
          SELECT vendor proveedor, round(sum(amount),2) compras, uniqExact(purchase_id) ordenes_compra
          FROM fact_purchases
          WHERE lowerUTF8(status) IN ('recibida','recibido','received','parcial','enviada','sent')
          GROUP BY proveedor
        ), names AS (
          SELECT proveedor FROM s UNION DISTINCT SELECT proveedor FROM p
        )
        SELECT names.proveedor proveedor, ifNull(s.pedidos,0) pedidos, ifNull(s.unidades,0) unidades,
               round(ifNull(s.ingresos,0),2) ingresos, round(ifNull(s.costos,0),2) costos,
               round(ifNull(s.utilidad,0),2) utilidad, ifNull(s.margen_pct,0) margen_pct,
               round(ifNull(p.compras,0),2) compras, ifNull(p.ordenes_compra,0) ordenes_compra,
               round(if(ifNull(p.compras,0)>0, ifNull(s.utilidad,0)/p.compras*100, 0),2) retorno_pct
        FROM names LEFT JOIN s ON names.proveedor=s.proveedor LEFT JOIN p ON names.proveedor=p.proveedor
        ORDER BY utilidad DESC, ingresos DESC, compras DESC
        LIMIT {limit:UInt16}
        SETTINGS prefer_column_name_to_alias = 1
    """, {"limit": limit})
    items = []
    for row in rows:
        utilidad = float(row.get("utilidad") or 0)
        compras = float(row.get("compras") or 0)
        retorno = float(row.get("retorno_pct") or 0)
        if utilidad <= 0 and compras > 0:
            decision = "Renegociar o reducir compras."
            level = "danger"
        elif retorno >= 40:
            decision = "Proveedor estratégico: asegurar abastecimiento."
            level = "ok"
        elif retorno >= 15:
            decision = "Mantener y comparar condiciones."
            level = "info"
        elif compras == 0 and utilidad > 0:
            decision = "Revisar trazabilidad de compras."
            level = "warn"
        else:
            decision = "Vigilar margen antes de escalar."
            level = "warn"
        items.append({**row, "decision": decision, "level": level})
    total_profit = round(sum(float(row.get("utilidad") or 0) for row in rows), 2)
    total_purchases = round(sum(float(row.get("compras") or 0) for row in rows), 2)
    best = items[0] if items else {}
    risk = [row for row in items if row.get("level") in ("danger", "warn")]
    return {
        "ready": True,
        "source": "clickhouse",
        "items": items,
        "summary": {
            "providers": len(items),
            "profit": total_profit,
            "purchases": total_purchases,
            "return_pct": round(total_profit / total_purchases * 100, 2) if total_purchases else 0,
            "best_provider": best.get("proveedor") or "—",
            "providers_to_review": len(risk),
        },
        "method": "Utilidad de ventas por productos asociados al proveedor, comparada con compras recibidas/enviadas.",
    }


def low_stock(*, threshold: int = 20, limit: int = 25) -> dict[str, Any]:
    """SKUs con inventario bajo en vitrina."""
    db = get_db()
    threshold = max(0, int(threshold))
    limit = max(5, min(int(limit), 100))
    query = {"inventory_quantity": {"$lte": threshold}}
    total_skus = db["product_variants"].count_documents({})
    low_count = db["product_variants"].count_documents(query)
    rows = list(
        db["product_variants"]
        .find(query, {"_id": 0})
        .sort("inventory_quantity", 1)
        .limit(limit)
    )
    out = []
    for v in rows:
        prod = db["products"].find_one({"product_id": v.get("product_id")}, {"_id": 0, "title": 1, "vendor_id": 1})
        vendor = None
        if prod and prod.get("vendor_id"):
            vendor = db["vendors"].find_one({"vendor_id": prod["vendor_id"]}, {"_id": 0, "name": 1})
        out.append(
            {
                "variant_id": v.get("variant_id"),
                "product_id": v.get("product_id"),
                "sku": v.get("sku"),
                "title": (prod or {}).get("title") or f"Producto {v.get('product_id')}",
                "inventory_quantity": int(v.get("inventory_quantity") or 0),
                "price": float(v.get("price") or 0),
                "cost": float(v.get("cost") or 0),
                "vendor_id": (prod or {}).get("vendor_id"),
                "vendor": (vendor or {}).get("name") or "—",
            }
        )
    insight = None
    if low_count:
        insight = (
            f"{low_count} SKU(s) en o bajo {threshold} uds. "
            f"Reponer con el proveedor o pausar venta de los críticos."
        )
    elif total_skus == 0:
        insight = "No hay catálogo de tienda. Ejecuta Sync catálogo en Maestros."
    else:
        insight = f"Stock saludable: ningún SKU ≤ {threshold} uds."
    return {
        "threshold": threshold,
        "total_skus": total_skus,
        "low_count": low_count,
        "items": out,
        "insight": insight,
    }


def commercial_funnel(*, days: int = 7) -> dict[str, Any]:
    """Embudo comercial B2B de los últimos N días + pendientes abiertos."""
    db = get_db()
    days = max(1, min(int(days), 90))
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    col = db["purchase_requests"]

    created = list(
        col.aggregate(
            [
                {"$match": {"created_at": {"$gte": since}}},
                {"$group": {"_id": "$status", "n": {"$sum": 1}}},
            ]
        )
    )
    by_status = {row["_id"]: int(row["n"]) for row in created if row.get("_id")}
    total_created = sum(by_status.values())
    converted = (
        by_status.get("convertida", 0)
        + by_status.get("enviada", 0)
        + by_status.get("entregada", 0)
    )
    rejected = by_status.get("rechazada", 0) + by_status.get("cancelada", 0)
    open_pipeline = col.count_documents(
        {"status": {"$in": ["pendiente", "en_revision", "aprobada", "convertida", "enviada"]}}
    )
    awaiting = col.count_documents({"status": {"$in": ["pendiente", "en_revision"]}})
    conversion_rate = round((converted / total_created) * 100.0, 1) if total_created else None

    stages = [
        {"key": "pendiente", "label": "Pendiente", "count": by_status.get("pendiente", 0)},
        {"key": "en_revision", "label": "En revisión", "count": by_status.get("en_revision", 0)},
        {"key": "aprobada", "label": "Aprobada", "count": by_status.get("aprobada", 0)},
        {"key": "convertida", "label": "Convertida", "count": by_status.get("convertida", 0)},
        {"key": "enviada", "label": "Enviada", "count": by_status.get("enviada", 0)},
        {"key": "entregada", "label": "Entregada", "count": by_status.get("entregada", 0)},
        {"key": "rechazada", "label": "Rechazada", "count": by_status.get("rechazada", 0)},
        {"key": "cancelada", "label": "Cancelada", "count": by_status.get("cancelada", 0)},
    ]

    insight = (
        f"Últimos {days} días: {total_created} solicitudes · "
        f"{converted} convertidas/envío · tasa {conversion_rate if conversion_rate is not None else '—'}%. "
        f"Cola abierta: {awaiting} por gestionar."
    )
    return {
        "days": days,
        "since": since,
        "total_created": total_created,
        "converted": converted,
        "rejected_or_cancelled": rejected,
        "conversion_rate": conversion_rate,
        "open_pipeline": open_pipeline,
        "awaiting_action": awaiting,
        "by_status": by_status,
        "stages": stages,
        "insight": insight,
    }


def build_alerts(
    margin: dict[str, Any],
    stock: dict[str, Any],
    funnel: dict[str, Any],
    channels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    if funnel.get("awaiting_action", 0) > 0:
        alerts.append(
            {
                "level": "warn",
                "code": "funnel_backlog",
                "title": "Solicitudes sin atender",
                "detail": f"{funnel['awaiting_action']} en pendiente/revisión. Prioriza la bandeja comercial.",
                "action": "ventas",
            }
        )
    rate = funnel.get("conversion_rate")
    if rate is not None and funnel.get("total_created", 0) >= 3 and rate < 25:
        alerts.append(
            {
                "level": "danger",
                "code": "low_conversion",
                "title": "Conversión comercial baja",
                "detail": f"Solo {rate}% de solicitudes terminaron en venta en el periodo.",
                "action": "ventas",
            }
        )
    if stock.get("low_count", 0) > 0:
        alerts.append(
            {
                "level": "warn",
                "code": "low_stock",
                "title": "Riesgo de quiebre de stock",
                "detail": stock.get("insight") or f"{stock['low_count']} SKUs bajos.",
                "action": "compras",
            }
        )
    bottom = (margin.get("bottom") or [])
    if bottom and bottom[0].get("margin_pct") is not None and bottom[0]["margin_pct"] < 10:
        alerts.append(
            {
                "level": "info",
                "code": "weak_margin",
                "title": "Categoría con margen débil",
                "detail": (
                    f"'{bottom[0]['item_type']}' rinde {bottom[0]['margin_pct']}%. "
                    f"Evalúa costo, precio o salida del portafolio."
                ),
                "action": "products",
            }
        )
    if channels:
        best = channels[0]
        alerts.append(
            {
                "level": "ok",
                "code": "best_channel",
                "title": "Canal más rentable",
                "detail": f"{best.get('channel')} · margen {best.get('margin_pct')}% · utilidad ${float(best.get('profit') or 0):,.0f}",
                "action": "regions",
            }
        )
    if not alerts:
        alerts.append(
            {
                "level": "ok",
                "code": "stable",
                "title": "Sin alertas críticas",
                "detail": "Embudo, stock y márgenes sin señales urgentes en este corte.",
                "action": "dashboard",
            }
        )
    return alerts


def decision_panel(
    *,
    days: int = 7,
    stock_threshold: int = 20,
    limit: int = 8,
) -> dict[str, Any]:
    key = (int(days), int(stock_threshold), int(limit))
    with _PANEL_CACHE_LOCK:
        cached = _PANEL_CACHE.get(key)
        if cached and monotonic() - cached[0] < _PANEL_CACHE_TTL:
            return {**cached[1], "cached": True}

    def operational_group():
        return low_stock(threshold=stock_threshold, limit=20), commercial_funnel(days=days)
    with ThreadPoolExecutor(max_workers=2) as pool:
        operational_future = pool.submit(operational_group)
        profit_future = pool.submit(true_profitability, limit=20)
        # Las consultas ClickHouse comparten sesión HTTP y deben ejecutarse en serie.
        margin = product_margin_ranking(limit=limit)
        channels = channel_margin_ranking(limit=6)
        portfolio = product_portfolio(lookback_days=max(90, days), limit=20)
        forecast = demand_forecast(months=12, horizon=3, limit=12)
        suppliers = supplier_profitability(limit=12)
        stock, funnel = operational_future.result()
        profitability = profit_future.result()
    alerts = (portfolio.get("recommendations") or []) + build_alerts(margin, stock, funnel, channels)
    result = {
        "generated_at": date.today().isoformat(),
        "margin": margin,
        "stock": {**stock, "data_layer": "operativo"},
        "funnel": {**funnel, "data_layer": "operativo"},
        "channels": channels,
        "portfolio": portfolio,
        "forecast": forecast,
        "suppliers": suppliers,
        "profitability": profitability,
        "alerts": alerts,
        "layers": {
            "margin": "estrategico",
            "channels": "estrategico",
            "stock": "operativo",
            "funnel": "operativo",
            "portfolio": "estrategico_clickhouse",
            "forecast": "estrategico_clickhouse",
            "suppliers": "estrategico_clickhouse",
            "profitability": "operativo_contable",
        },
        "strategic_ready": bool(margin.get("strategic_ready")),
    }
    with _PANEL_CACHE_LOCK:
        _PANEL_CACHE[key] = (monotonic(), result)
        if len(_PANEL_CACHE) > 12:
            oldest = min(_PANEL_CACHE, key=lambda item: _PANEL_CACHE[item][0])
            _PANEL_CACHE.pop(oldest, None)
    return result
