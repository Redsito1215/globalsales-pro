"""Servicios de la consola profesional de Altavia Trade."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db, json_safe


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(collection: str, field: str) -> int:
    row = get_db()[collection].find_one({}, {field: 1, "_id": 0}, sort=[(field, -1)])
    return int((row or {}).get(field) or 0) + 1


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value or "")[:10]).date()
    except (TypeError, ValueError):
        return None


def _aggregate_sales(match: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = list(get_db()["fact_ventas"].aggregate([
        {"$match": match or {}},
        {"$group": {"_id": None, "orders": {"$sum": 1}, "units": {"$sum": "$units_sold"},
                    "revenue": {"$sum": "$total_revenue"}, "profit": {"$sum": "$total_profit"}}},
    ]))
    row = rows[0] if rows else {}
    revenue = _money(row.get("revenue"))
    profit = _money(row.get("profit"))
    return {"orders": int(row.get("orders") or 0), "units": int(row.get("units") or 0),
            "revenue": revenue, "profit": profit,
            "margin": round(profit / revenue * 100, 2) if revenue else 0.0}


def professional_home(role: str | None) -> dict[str, Any]:
    db = get_db()
    sales = _aggregate_sales()
    pending_orders = db["purchase_requests"].count_documents({"status": {"$in": ["pendiente", "en_revision"]}})
    low_stock = db["product_variants"].count_documents({"inventory_quantity": {"$lte": 20}})
    pending_approvals = db["management_approvals"].count_documents({"status": "pending"})
    role_key = (role or "usuario").lower()
    quick_by_role = {
        "administrador": [("Aprobaciones", 7), ("Calidad de datos", 9), ("Metas", 6)],
        "gerente": [("Alertas", 2), ("Metas", 6), ("Proveedores", 5)],
        "vendedor": [("Clientes 360", 4), ("Productos 360", 3), ("Búsqueda", 10)],
    }
    quick = quick_by_role.get(role_key, [("Alertas", 2), ("Búsqueda", 10), ("Productos 360", 3)])
    return {"role": role_key, "kpis": [
        {"label": "Ingresos históricos", "value": sales["revenue"], "format": "money"},
        {"label": "Margen", "value": sales["margin"], "format": "percent"},
        {"label": "Pedidos por revisar", "value": pending_orders, "format": "number"},
        {"label": "Stock bajo", "value": low_stock, "format": "number"},
    ], "pending_approvals": pending_approvals,
        "quick_actions": [{"label": label, "phase": phase} for label, phase in quick]}


def action_alerts(stock_threshold: int = 20) -> list[dict[str, Any]]:
    db = get_db()
    alerts: list[dict[str, Any]] = []
    low = db["product_variants"].count_documents({"inventory_quantity": {"$lte": int(stock_threshold)}})
    pending = db["purchase_requests"].count_documents({"status": {"$in": ["pendiente", "en_revision"]}})
    approvals = db["management_approvals"].count_documents({"status": "pending"})
    failed = db["system_errors"].count_documents({})
    today = date.today().isoformat()
    late_shipments = db["purchase_requests"].count_documents(
        {"status": "enviada", "estimated_delivery": {"$lt": today, "$nin": [None, ""]}}
    )
    if low:
        alerts.append({"id": "low-stock", "severity": "high", "title": "Inventario por debajo del umbral",
                       "detail": f"{low} variantes requieren revisión de reposición.", "value": low,
                       "action": "Abrir compras e inventario", "page": "compras"})
    if pending:
        alerts.append({"id": "pending-orders", "severity": "medium", "title": "Pedidos esperando revisión",
                       "detail": f"Hay {pending} pedidos pendientes o en revisión.", "value": pending,
                       "action": "Revisar pedidos", "page": "ventas"})
    if approvals:
        alerts.append({"id": "pending-approvals", "severity": "medium", "title": "Decisiones pendientes",
                       "detail": f"{approvals} solicitudes requieren una decisión.", "value": approvals,
                       "action": "Abrir aprobaciones", "phase": 7})
    if failed:
        alerts.append({"id": "data-errors", "severity": "low", "title": "Incidencias registradas",
                       "detail": f"El registro técnico contiene {failed} incidencias.", "value": failed,
                       "action": "Revisar calidad", "phase": 9})
    if late_shipments:
        alerts.append({"id": "late-shipments", "severity": "high", "title": "Entregas atrasadas",
                       "detail": f"{late_shipments} envíos superaron su fecha estimada.", "value": late_shipments,
                       "action": "Gestionar logística", "phase": 11})
    return alerts


def product_profile(product_id: int) -> dict[str, Any] | None:
    db = get_db()
    product = db["products"].find_one({"product_id": int(product_id)}, {"_id": 0})
    if not product:
        product = db["dim_producto"].find_one({"product_id": int(product_id)}, {"_id": 0})
    if not product:
        return None
    variants = list(db["product_variants"].find({"product_id": int(product_id)}, {"_id": 0}).limit(50))
    vendor = db["vendors"].find_one({"vendor_id": product.get("vendor_id")}, {"_id": 0}) if product.get("vendor_id") else None
    sales = _aggregate_sales({"product_id": int(product_id)})
    variant_ids = [v.get("variant_id") for v in variants if v.get("variant_id") is not None]
    moves = list(db["inventory_movements"].find({"variant_id": {"$in": variant_ids}}, {"_id": 0}).sort("created_at", -1).limit(15)) if variant_ids else []
    stock = sum(int(v.get("inventory_quantity") or 0) for v in variants)
    prices = [float(v.get("price") or 0) for v in variants]
    costs = [float(v.get("cost") or 0) for v in variants]
    return json_safe({"product": product, "vendor": vendor, "variants": variants, "sales": sales,
                      "stock": stock, "average_price": _money(sum(prices) / len(prices) if prices else 0),
                      "average_cost": _money(sum(costs) / len(costs) if costs else 0), "movements": moves})


def customer_profile(client_id: int) -> dict[str, Any] | None:
    db = get_db()
    customer = db["dim_cliente"].find_one({"client_id": int(client_id)}, {"_id": 0})
    if not customer:
        customer = db["customers"].find_one({"customer_id": int(client_id)}, {"_id": 0})
    if not customer:
        return None
    email = str(customer.get("email") or "").lower()
    query = {"client_email": email} if email else {"client_id": int(client_id)}
    orders = list(db["purchase_requests"].find(query, {"_id": 0}).sort("created_at", -1).limit(25))
    total = sum(float(row.get("total") or row.get("total_amount") or 0) for row in orders
                if row.get("status") not in {"rechazada", "cancelada"})
    last_at = next((row.get("created_at") for row in orders if row.get("created_at")), None)
    return json_safe({"customer": customer, "summary": {"orders": len(orders), "total_spent": _money(total),
                      "average_order": _money(total / len(orders) if orders else 0), "last_activity": last_at,
                      "segment": customer.get("segment") or "sin clasificar"}, "orders": orders[:10]})


def vendor_evaluation() -> list[dict[str, Any]]:
    db = get_db()
    vendors = list(db["vendors"].find({}, {"_id": 0}).sort("name", 1))
    result = []
    for vendor in vendors:
        vid = vendor.get("vendor_id")
        orders = list(db["purchase_orders"].find({"vendor_id": vid}, {"_id": 0}))
        ids = [x.get("po_id") for x in orders]
        lines = list(db["purchase_order_lines"].find({"po_id": {"$in": ids}}, {"_id": 0})) if ids else []
        amount = sum(float(x.get("unit_cost") or 0) * int(x.get("quantity_ordered") or 0) for x in lines)
        ordered = sum(int(x.get("quantity_ordered") or 0) for x in lines)
        received = sum(int(x.get("quantity_received") or 0) for x in lines)
        fulfillment = round(received / ordered * 100, 1) if ordered else 0.0
        completed = [o for o in orders if o.get("received_at")]
        lead_days = []
        on_time = 0
        for order in completed:
            created, received = _as_date(order.get("created_at")), _as_date(order.get("received_at"))
            if created and received:
                days = max((received - created).days, 0)
                lead_days.append(days)
                promised = int(order.get("expected_lead_days") or vendor.get("lead_time_days") or 14)
                on_time += int(days <= promised)
        avg_lead = round(sum(lead_days) / len(lead_days), 1) if lead_days else None
        on_time_rate = round(on_time / len(lead_days) * 100, 1) if lead_days else None
        timing_score = on_time_rate if on_time_rate is not None else 50.0
        score = min(100, round(fulfillment * .55 + timing_score * .35 + min(len(orders), 10), 1)) if orders else 0.0
        result.append({"vendor_id": vid, "name": vendor.get("name"), "active": vendor.get("active", True),
                       "orders": len(orders), "amount": _money(amount), "fulfillment": fulfillment, "score": score,
                       "average_lead_days": avg_lead, "on_time_rate": on_time_rate,
                       "rating": "Excelente" if score >= 90 else "Confiable" if score >= 70 else "En evaluación" if score else "Sin actividad"})
    return sorted(result, key=lambda x: (x["score"], x["amount"]), reverse=True)


def _goal_actual(metric: str) -> float:
    sales = _aggregate_sales()
    return float(sales.get(metric) or 0)


def list_goals() -> list[dict[str, Any]]:
    rows = list(get_db()["management_goals"].find({}, {"_id": 0}).sort("goal_id", -1).limit(100))
    for row in rows:
        actual = _goal_actual(row.get("metric") or "revenue")
        target = float(row.get("target") or 0)
        row.update({"actual": round(actual, 2), "progress": round(actual / target * 100, 1) if target else 0,
                    "gap": round(target - actual, 2)})
    return json_safe(rows)


def create_goal(data: dict[str, Any], owner_email: str | None = None) -> dict[str, Any]:
    name = str(data.get("name") or "").strip()
    metric = str(data.get("metric") or "revenue").strip()
    target = float(data.get("target") or 0)
    start, end = str(data.get("period_start") or ""), str(data.get("period_end") or "")
    if len(name) < 3 or metric not in {"revenue", "orders", "profit", "margin"} or target <= 0 or not start or not end or start > end:
        raise ValueError("invalid_goal")
    doc = {"goal_id": _next_id("management_goals", "goal_id"), "name": name[:100], "metric": metric,
           "target": target, "period_start": start, "period_end": end, "status": "active",
           "owner_email": owner_email, "created_at": _now(), "updated_at": _now()}
    get_db()["management_goals"].insert_one(doc)
    log_audit("create_management_goal", entity="management_goals", entity_id=doc["goal_id"], details=doc)
    return next(x for x in list_goals() if x["goal_id"] == doc["goal_id"])


def list_approvals(status: str | None = None) -> list[dict[str, Any]]:
    query = {"status": status} if status in {"pending", "approved", "rejected"} else {}
    return json_safe(list(get_db()["management_approvals"].find(query, {"_id": 0}).sort("approval_id", -1).limit(100)))


def create_approval(data: dict[str, Any], requester_email: str | None = None) -> dict[str, Any]:
    title, reason = str(data.get("title") or "").strip(), str(data.get("reason") or "").strip()
    amount = float(data.get("amount") or 0)
    if len(title) < 3 or len(reason) < 5 or amount < 0:
        raise ValueError("invalid_approval")
    doc = {"approval_id": _next_id("management_approvals", "approval_id"), "type": str(data.get("type") or "general")[:40],
           "title": title[:120], "reason": reason[:500], "reference": str(data.get("reference") or "")[:80] or None,
           "amount": amount, "status": "pending", "requester_email": requester_email, "reviewer_email": None,
           "created_at": _now(), "decided_at": None, "comment": None}
    get_db()["management_approvals"].insert_one(doc)
    log_audit("create_management_approval", entity="management_approvals", entity_id=doc["approval_id"], details=doc)
    return json_safe(doc)


def decide_approval(approval_id: int, decision: str, reviewer_email: str | None, comment: str = "") -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("invalid_decision")
    db = get_db()
    current = db["management_approvals"].find_one({"approval_id": int(approval_id)}, {"_id": 0})
    if not current:
        raise ValueError("not_found")
    if current.get("status") != "pending":
        raise ValueError("already_decided")
    patch = {"status": decision, "reviewer_email": reviewer_email, "decided_at": _now(), "comment": comment[:500] or None}
    db["management_approvals"].update_one({"approval_id": int(approval_id)}, {"$set": patch})
    log_audit("decide_management_approval", entity="management_approvals", entity_id=approval_id,
              before=current, after={**current, **patch})
    return json_safe({**current, **patch})


def readable_history(entity: str | None = None, entity_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if entity:
        query["entity"] = entity
    if entity_id:
        query["entity_id"] = {"$in": [entity_id, int(entity_id)]} if entity_id.isdigit() else entity_id
    rows = list(get_db()["audit_log"].find(query, {"_id": 0}).sort("at", -1).limit(min(max(limit, 1), 200)))
    return json_safe(rows)


def data_quality() -> list[dict[str, Any]]:
    db = get_db()
    specs = [("Productos", "products", "updated_at"), ("Clientes", "dim_cliente", "updated_at"),
             ("Pedidos", "purchase_requests", "created_at"), ("Ventas analíticas", "fact_ventas", "order_date"),
             ("Proveedores", "vendors", "updated_at"), ("Auditoría", "audit_log", "at")]
    out = []
    for label, collection, date_field in specs:
        try:
            count = db[collection].count_documents({})
            latest = db[collection].find_one({date_field: {"$exists": True}}, {date_field: 1, "_id": 0}, sort=[(date_field, -1)])
            out.append({"source": label, "collection": collection, "status": "ok" if count else "empty",
                        "records": count, "last_update": (latest or {}).get(date_field),
                        "detail": "Disponible" if count else "Sin registros"})
        except Exception as exc:
            out.append({"source": label, "collection": collection, "status": "error", "records": 0,
                        "last_update": None, "detail": str(exc)[:120]})
    return json_safe(out)


def logistics_overview(limit: int = 30) -> dict[str, Any]:
    db = get_db()
    active_statuses = ["aprobada", "convertida", "enviada"]
    rows = list(db["purchase_requests"].find(
        {"status": {"$in": active_statuses}}, {"_id": 0}
    ).sort("request_id", -1).limit(min(max(limit, 1), 100)))
    delivered = list(db["purchase_requests"].find(
        {"status": "entregada", "shipped_at": {"$nin": [None, ""]}, "delivered_at": {"$nin": [None, ""]}},
        {"_id": 0, "shipped_at": 1, "delivered_at": 1, "estimated_delivery": 1},
    ).sort("request_id", -1).limit(1000))
    transit_days, on_time = [], 0
    for row in delivered:
        shipped, received = _as_date(row.get("shipped_at")), _as_date(row.get("delivered_at"))
        if shipped and received:
            days = max((received - shipped).days, 0)
            transit_days.append(days)
            promised = _as_date(row.get("estimated_delivery")) or shipped.replace(day=shipped.day)
            on_time += int(received <= promised) if row.get("estimated_delivery") else int(days <= 7)
    for row in rows:
        row["carrier"] = row.get("carrier") or "Transporte interno"
        row["tracking_number"] = row.get("tracking_number") or "Pendiente"
        row["estimated_delivery"] = row.get("estimated_delivery")
    return json_safe({
        "summary": {
            "preparing": db["purchase_requests"].count_documents({"status": {"$in": ["aprobada", "convertida"]}}),
            "in_transit": db["purchase_requests"].count_documents({"status": "enviada"}),
            "average_transit_days": round(sum(transit_days) / len(transit_days), 1) if transit_days else None,
            "delivery_target_days": 7,
            "on_time_rate": round(on_time / len(transit_days) * 100, 1) if transit_days else None,
            "late": db["purchase_requests"].count_documents(
                {"status": "enviada", "estimated_delivery": {"$lt": date.today().isoformat(), "$nin": [None, ""]}}
            ),
        },
        "shipments": rows,
    })


def demand_forecast(limit: int = 12) -> list[dict[str, Any]]:
    """Adapta el pronóstico estratégico de ClickHouse a la consola profesional."""
    from paquetes.decisiones.services import demand_forecast as strategic_forecast

    result = strategic_forecast(months=12, horizon=3, limit=limit)
    if not result.get("ready"):
        return []
    rows = []
    for item in result.get("items") or []:
        monthly = round(float(item.get("forecast_total") or 0) / 3, 1)
        stock = float(item.get("stock") or 0)
        rows.append({"product_id": item.get("product_id"), "product": item.get("product"),
                     "monthly_forecast": monthly, "current_stock": stock,
                     "coverage_months": round(stock / monthly, 1) if monthly else None,
                     "suggested_reorder": int(item.get("recommended_purchase") or 0),
                     "forecast": item.get("forecast") or [], "confidence": item.get("confidence"),
                     "confidence_pct": item.get("confidence_pct"), "method": result.get("method")})
    if rows:
        return json_safe(rows)
    # El histórico heredado no siempre posee product_id. Mantener el gráfico útil
    # con una proyección por categoría, sin habilitar requisición automática.
    try:
        from paquetes.decisiones.services import _forecast_values
        from shared.clickhouse import query_rows
        raw = query_rows("""
            WITH (SELECT max(sale_date) FROM fact_sales WHERE product_id=0) AS anchor
            SELECT category, toStartOfMonth(sale_date) month, sum(units) units
            FROM fact_sales WHERE product_id=0 AND sale_date >= addMonths(toStartOfMonth(anchor), -11)
            GROUP BY category, month ORDER BY category, month
        """)
        grouped: dict[str, list[float]] = {}
        for item in raw:
            grouped.setdefault(str(item.get("category") or "Sin categoría"), []).append(float(item.get("units") or 0))
        fallback = []
        for category, values in grouped.items():
            calc = _forecast_values(values, 3)
            if calc.get("forecast"):
                fallback.append({"product_id": 0, "product": category, "forecast": calc["forecast"],
                                 "monthly_forecast": round(sum(calc["forecast"]) / 3, 1), "current_stock": 0,
                                 "coverage_months": None, "suggested_reorder": 0,
                                 "confidence": calc.get("confidence"), "confidence_pct": calc.get("confidence_pct"),
                                 "method": "pronóstico estratégico por categoría"})
        fallback.sort(key=lambda x: x["monthly_forecast"], reverse=True)
        return json_safe(fallback[:limit])
    except Exception:
        return []


def profitability_summary() -> dict[str, Any]:
    db = get_db()
    sales = _aggregate_sales()
    orders = list(db["purchase_requests"].find({}, {"_id": 0, "discount_amount": 1, "shipping_cost": 1}))
    discounts = sum(float(x.get("discount_amount") or 0) for x in orders)
    logistics = sum(float(x.get("shipping_cost") or 0) for x in orders)
    refunds = sum(float(x.get("amount") or 0) for x in db["cash_movements"].find(
        {"movement_type": "refund_out"}, {"_id": 0, "amount": 1}))
    waste = 0.0
    for item in db["inventory_scrapped"].find({}, {"_id": 0, "variant_id": 1, "quantity": 1}):
        variant = db["product_variants"].find_one(
            {"variant_id": item.get("variant_id")}, {"_id": 0, "cost": 1, "unit_cost": 1}
        ) or {}
        waste += int(item.get("quantity") or 0) * float(variant.get("cost") or variant.get("unit_cost") or 0)
    adjusted = sales["profit"] - refunds - logistics - waste
    return {"revenue": sales["revenue"], "gross_profit": sales["profit"], "discounts": _money(discounts),
            "refunds": _money(refunds), "logistics": _money(logistics), "waste": _money(waste),
            "adjusted_profit": _money(adjusted),
            "adjusted_margin": round(adjusted / sales["revenue"] * 100, 2) if sales["revenue"] else 0.0}


def loyalty_overview(limit: int = 12) -> dict[str, Any]:
    db = get_db()
    pipeline = [
        {"$match": {"status": {"$nin": ["rechazada", "cancelada"]}}},
        {"$group": {"_id": "$client_email", "name": {"$first": "$client_name"},
                    "orders": {"$sum": 1}, "spent": {"$sum": "$total"}, "last": {"$max": "$created_at"}}},
        {"$sort": {"spent": -1}}, {"$limit": min(max(limit, 1), 50)},
    ]
    customers = []
    for row in db["purchase_requests"].aggregate(pipeline):
        orders, spent = int(row.get("orders") or 0), float(row.get("spent") or 0)
        segment = "VIP" if orders >= 8 or spent >= 5000 else "Frecuente" if orders >= 3 else "Nuevo"
        last = _as_date(row.get("last"))
        inactive = bool(last and (date.today() - last).days > 90)
        customers.append({"email": row.get("_id"), "name": row.get("name"), "orders": orders,
                          "spent": _money(spent), "last_activity": row.get("last"), "segment": segment,
                          "attention": "Reactivar" if inactive else "Mantener" if segment != "Nuevo" else "Acompañar"})
    return json_safe({"customers": customers, "summary": {
        "vip": sum(x["segment"] == "VIP" for x in customers),
        "frequent": sum(x["segment"] == "Frecuente" for x in customers),
        "reactivate": sum(x["attention"] == "Reactivar" for x in customers),
    }})


def quality_issues(limit: int = 20) -> dict[str, Any]:
    db = get_db()
    rules = [
        ("Productos sin categoría", "products", {"$or": [{"category_id": None}, {"category_id": {"$exists": False}}]}),
        ("Productos sin proveedor", "products", {"$or": [{"vendor_id": None}, {"vendor_id": {"$exists": False}}]}),
        ("Variantes con precio inválido", "product_variants", {"price": {"$lte": 0}}),
        ("Variantes con stock negativo", "product_variants", {"inventory_quantity": {"$lt": 0}}),
        ("Proveedores sin correo", "vendors", {"$or": [{"email": ""}, {"email": None}, {"email": {"$exists": False}}]}),
        ("Pedidos sin país", "purchase_requests", {"$or": [{"country_id": None}, {"country_id": {"$exists": False}}]}),
    ]
    issues = [{"rule": label, "collection": collection, "count": db[collection].count_documents(query)}
              for label, collection, query in rules]
    return {"total": sum(x["count"] for x in issues), "issues": issues[:limit]}


def update_shipment(request_id: int, data: dict[str, Any], actor_email: str | None = None) -> dict[str, Any]:
    db = get_db()
    current = db["purchase_requests"].find_one({"request_id": int(request_id)}, {"_id": 0})
    if not current:
        raise ValueError("not_found")
    if current.get("status") not in {"aprobada", "convertida", "enviada"}:
        raise ValueError("shipment_closed")
    estimate = str(data.get("estimated_delivery") or "").strip()
    if estimate and not _as_date(estimate):
        raise ValueError("invalid_delivery_date")
    patch = {
        "carrier": str(data.get("carrier") or current.get("carrier") or "Transporte interno").strip()[:80],
        "tracking_number": str(data.get("tracking_number") or current.get("tracking_number") or "").strip()[:80] or None,
        "estimated_delivery": estimate or current.get("estimated_delivery"),
        "logistics_updated_at": _now(),
    }
    db["purchase_requests"].update_one({"request_id": int(request_id)}, {"$set": patch})
    log_audit("update_shipment", entity="purchase_requests", entity_id=request_id,
              before={key: current.get(key) for key in patch}, after=patch,
              details={"actor": actor_email})
    return json_safe({**current, **patch})


def create_forecast_requisition(product_id: int, quantity: int) -> dict[str, Any]:
    if quantity < 1:
        raise ValueError("invalid_reorder_quantity")
    db = get_db()
    product = db["products"].find_one({"product_id": int(product_id)}, {"_id": 0}) or {}
    variant = db["product_variants"].find_one({"product_id": int(product_id)}, {"_id": 0}, sort=[("variant_id", 1)])
    if not variant:
        raise ValueError("variant_not_found")
    vendor_id = int(variant.get("vendor_id") or product.get("vendor_id") or 0)
    if not vendor_id:
        raise ValueError("vendor_required")
    from paquetes.compras.services import create_purchase_requisition

    return create_purchase_requisition({"vendor_id": vendor_id,
        "notes": "Generada desde el pronóstico estratégico de demanda.",
        "lines": [{"variant_id": int(variant["variant_id"]), "quantity": int(quantity),
                   "unit_cost": float(variant.get("cost") or 0)}]})


def create_loyalty_campaign(segment: str, actor_email: str | None = None) -> dict[str, Any]:
    segment = str(segment or "").strip().lower()
    config = {"vip": (12, 100), "frecuente": (8, 200), "reactivar": (15, 100)}
    if segment not in config:
        raise ValueError("invalid_campaign_segment")
    percentage, minimum = config[segment]
    from shared.commercial import save_discount

    code = f"ALTAVIA-{segment.upper()}-{date.today().strftime('%m%d')}"
    return save_discount({"code": code, "value_type": "percentage", "value": percentage,
                          "usage_limit": 100, "minimum_order_amount": minimum,
                          "allowed_segments": [segment], "active": True}, actor_email=actor_email)


def analytics_freshness() -> dict[str, Any]:
    db = get_db()
    mongo = db["fact_ventas"].find_one({}, {"order_date": 1, "_id": 0}, sort=[("order_date", -1)]) or {}
    clickhouse = None
    try:
        from shared.clickhouse import query_rows
        rows = query_rows("SELECT loaded_at,status FROM etl_runs ORDER BY loaded_at DESC LIMIT 1")
        clickhouse = rows[0] if rows else None
    except Exception:
        clickhouse = None
    return json_safe({"mongo_last_sale": mongo.get("order_date"), "clickhouse_last_load": (clickhouse or {}).get("loaded_at"),
                      "clickhouse_status": (clickhouse or {}).get("status") or "sin publicación"})


def clickhouse_monitor() -> dict[str, Any]:
    """Estado legible para que un gerente pueda comprobar la capa analítica."""
    tables = []
    try:
        from shared.clickhouse import ping_clickhouse, query_rows
        online = ping_clickhouse()
        if online:
            for name in ("fact_sales", "fact_purchases", "inventory_snapshot", "fact_logistics", "etl_runs"):
                rows = query_rows(f"SELECT count() records FROM {name}")
                tables.append({"table": name, "records": int((rows[0] if rows else {}).get("records") or 0)})
            last = query_rows("SELECT loaded_at,source,status,rows_sales,rows_purchases,rows_inventory,rows_logistics,message FROM etl_runs ORDER BY loaded_at DESC LIMIT 1")
        else:
            last = []
    except Exception as exc:
        online, last = False, []
        return {"online": False, "status": "sin conexión", "tables": [], "last_run": None,
                "detail": str(exc)[:180], "airflow_url": "http://localhost:8080", "http_url": "http://localhost:8123"}
    return json_safe({"online": online, "status": "operativo" if online else "sin conexión",
                      "tables": tables, "last_run": last[0] if last else None,
                      "airflow_url": "http://localhost:8080", "http_url": "http://localhost:8123"})


def inventory_lot_overview(*, expiring_days: int | None = None) -> dict[str, Any]:
    from shared.inventory_lots import list_lots
    rows = list_lots(expiring_days=expiring_days, include_empty=True)
    return {"items": json_safe(rows), "summary": {
        "lots": len(rows), "available_units": sum(int(x.get("quantity_available") or 0) for x in rows),
        "expired": sum(x.get("expiry_status") == "vencido" for x in rows),
        "expiring": sum(x.get("expiry_status") == "por_vencer" for x in rows),
    }}


def save_inventory_lot(data: dict[str, Any], actor_email: str | None = None) -> dict[str, Any]:
    from shared.inventory_lots import register_lot
    return register_lot(variant_id=int(data.get("variant_id") or 0), lot_code=data.get("lot_code"),
                        quantity=int(data.get("quantity") or 0), expiry_date=data.get("expiry_date"),
                        po_id=int(data.get("po_id") or 0) or None, actor_email=actor_email)


def lot_trace(lot_code: str) -> dict[str, Any]:
    from shared.inventory_lots import trace_lot
    return json_safe(trace_lot(lot_code))


def price_lists_overview() -> list[dict[str, Any]]:
    from shared.price_lists import list_price_lists
    return json_safe(list_price_lists())


def save_business_price_list(data: dict[str, Any], actor_email: str | None = None) -> dict[str, Any]:
    from shared.price_lists import save_price_list
    return json_safe(save_price_list(data, actor_email=actor_email))


def inventory_reconciliation() -> dict[str, Any]:
    db = get_db(); rows=[]
    for v in db["product_variants"].find({"inventory_quantity":{"$gt":1_000_000}},{"_id":0,"variant_id":1,"product_id":1,"sku":1,"inventory_quantity":1}).limit(500):
        p=db["products"].find_one({"product_id":v.get("product_id")},{"_id":0,"title":1}) or {}
        rows.append({**v,"product":p.get("title") or f"Producto {v.get('product_id')}","status":"requiere_conteo"})
    return {"items":rows,"total":len(rows),"message":"Registra el conteo físico real; no se reemplazan existencias automáticamente."}


def apply_inventory_counts(items: list[dict[str, Any]], actor_email: str | None=None) -> dict[str, Any]:
    from paquetes.compras.services import register_physical_count
    applied=[]
    for item in items or []:
        applied.append(register_physical_count(int(item.get("variant_id") or 0),counted=int(item.get("counted")),reason="Conciliación de inventario histórico",actor_email=actor_email))
    if not applied: raise ValueError("inventory_counts_required")
    return {"applied":len(applied),"items":applied}


def monthly_management_close(period: str, actor_email: str | None=None) -> dict[str, Any]:
    import calendar
    from shared.accounting import financial_summary, close_period
    year,month=map(int,str(period).split("-")); end=calendar.monthrange(year,month)[1]
    db=get_db(); snapshot={"financial":financial_summary(),"seller_performance":__import__('shared.sales_performance',fromlist=['overview']).overview(),
        "inventory_units":sum(int(x.get("inventory_quantity") or 0) for x in db["product_variants"].find({"inventory_quantity":{"$lte":1_000_000}},{"inventory_quantity":1})),
        "closed_at":_now(),"period":period}
    row=close_period(period_type="monthly",value=period,reason="Cierre gerencial mensual",actor_email=actor_email)
    db["management_monthly_closes"].update_one({"period":period},{"$set":{**snapshot,"accounting_period":row}},upsert=True)
    return json_safe(snapshot)


def backup_catalog() -> list[dict[str, Any]]:
    from pathlib import Path
    from shared.backup_status import list_backup_manifests
    return list_backup_manifests(Path(__file__).resolve().parents[2]/"backups",limit=50)


def profitability_comparison(limit: int = 10) -> dict[str, Any]:
    from paquetes.decisiones.services import true_profitability

    detail = true_profitability(limit=max(limit, 20))
    clients: dict[str, dict[str, Any]] = {}
    for order in detail.get("orders") or []:
        key = str(order.get("client") or "Sin cliente")
        row = clients.setdefault(key, {"name": key, "revenue": 0.0, "profit": 0.0, "orders": 0})
        row["revenue"] += float(order.get("net_revenue") or 0)
        row["profit"] += float(order.get("net_profit") or 0)
        row["orders"] += 1
    for row in clients.values():
        row["revenue"], row["profit"] = _money(row["revenue"]), _money(row["profit"])
        row["margin"] = round(row["profit"] / row["revenue"] * 100, 2) if row["revenue"] else 0.0
    strategic: dict[str, list[dict[str, Any]]] = {"categories": [], "regions": []}
    try:
        from shared.clickhouse import query_rows
        strategic["categories"] = query_rows(
            "SELECT category name,round(rev,2) revenue,round(gain,2) profit,round(if(rev>0,gain/rev*100,0),2) margin FROM (SELECT category,sum(revenue) rev,sum(profit) gain FROM fact_sales GROUP BY category) ORDER BY gain DESC LIMIT {limit:UInt16}", {"limit": limit})
        strategic["regions"] = query_rows(
            "SELECT region name,round(rev,2) revenue,round(gain,2) profit,round(if(rev>0,gain/rev*100,0),2) margin FROM (SELECT region,sum(revenue) rev,sum(profit) gain FROM fact_sales GROUP BY region) ORDER BY gain DESC LIMIT {limit:UInt16}", {"limit": limit})
    except Exception:
        pass
    products = [{"name": row.get("product"), "revenue": row.get("revenue"), "profit": row.get("profit"),
                 "margin": row.get("margin_pct")} for row in detail.get("products") or []]
    return json_safe({"products": products[:limit], "clients": sorted(clients.values(), key=lambda x: x["profit"], reverse=True)[:limit], **strategic})


def global_search(term: str, limit: int = 6) -> dict[str, list[dict[str, Any]]]:
    clean = term.strip()
    if len(clean) < 2:
        raise ValueError("query_too_short")
    rx = {"$regex": re.escape(clean), "$options": "i"}
    db, cap = get_db(), min(max(int(limit), 1), 20)
    groups: dict[str, list[dict[str, Any]]] = {"products": [], "customers": [], "vendors": [], "orders": []}
    for row in db["products"].find({"$or": [{"title": rx}, {"name": rx}, {"sku": rx}]}, {"_id": 0}).limit(cap):
        groups["products"].append({"id": row.get("product_id"), "title": row.get("title") or row.get("name"), "subtitle": "Producto", "phase": 3})
    for row in db["dim_cliente"].find({"$or": [{"name": rx}, {"email": rx}]}, {"_id": 0}).limit(cap):
        groups["customers"].append({"id": row.get("client_id"), "title": row.get("name") or row.get("email"), "subtitle": row.get("email") or "Cliente", "phase": 4})
    for row in db["vendors"].find({"$or": [{"name": rx}, {"email": rx}]}, {"_id": 0}).limit(cap):
        groups["vendors"].append({"id": row.get("vendor_id"), "title": row.get("name"), "subtitle": row.get("email") or "Proveedor", "phase": 5})
    order_terms: list[dict[str, Any]] = [{"client_email": rx}, {"client_name": rx}, {"order_id": rx}]
    if clean.isdigit():
        order_terms.append({"request_id": int(clean)})
    order_query = {"$or": order_terms}
    for row in db["purchase_requests"].find(order_query, {"_id": 0}).limit(cap):
        groups["orders"].append({"id": row.get("request_id"), "title": row.get("order_id") or f"Solicitud #{row.get('request_id')}", "subtitle": row.get("client_email") or "Pedido", "page": "ventas"})
    return json_safe(groups)
