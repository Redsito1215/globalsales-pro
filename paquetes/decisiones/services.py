"""Servicios de decisiones de negocio — margen (estratégico), stock y embudo (operativo)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from shared.data_layers import analytics_fact, strategic_ready
from shared.mongo import get_db


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
    margin = product_margin_ranking(limit=limit)
    stock = low_stock(threshold=stock_threshold, limit=20)
    funnel = commercial_funnel(days=days)
    channels = channel_margin_ranking(limit=6)
    alerts = build_alerts(margin, stock, funnel, channels)
    return {
        "generated_at": date.today().isoformat(),
        "margin": margin,
        "stock": {**stock, "data_layer": "operativo"},
        "funnel": {**funnel, "data_layer": "operativo"},
        "channels": channels,
        "alerts": alerts,
        "layers": {
            "margin": "estrategico",
            "channels": "estrategico",
            "stock": "operativo",
            "funnel": "operativo",
        },
        "strategic_ready": bool(margin.get("strategic_ready")),
    }
