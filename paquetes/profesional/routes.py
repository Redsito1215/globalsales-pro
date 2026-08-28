"""API de la consola profesional en 11 fases."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request, session

from auth.decorators import login_required, permission_required
from paquetes.profesional import services

profesional_bp = Blueprint("profesional", __name__, url_prefix="/api/profesional")


def _error(exc: ValueError):
    code = str(exc)
    messages = {"invalid_goal": "Completa correctamente la meta.", "invalid_approval": "Completa título, motivo y monto válido.",
                "invalid_decision": "La decisión debe ser aprobar o rechazar.", "already_decided": "La solicitud ya fue resuelta.",
                "not_found": "Registro no encontrado.", "query_too_short": "Escribe al menos dos caracteres.",
                "shipment_closed": "Este envío ya no admite cambios logísticos.",
                "invalid_delivery_date": "La fecha estimada no es válida."}
    messages.update({"invalid_reorder_quantity": "La cantidad de reposición no es válida.",
                     "variant_not_found": "El producto no tiene una variante comprable.",
                     "vendor_required": "Asigna un proveedor antes de crear la requisición.",
                     "invalid_campaign_segment": "El segmento de campaña no es válido."})
    messages.update({"invalid_lot": "Indica un lote y una cantidad válidos.",
                     "invalid_expiry_date": "La fecha de caducidad no es válida.",
                     "lot_expiry_conflict": "Ese lote ya existe con otra fecha de caducidad.",
                     "invalid_price_list": "Completa el nombre y tipo de lista de precios.",
                     "price_list_customer_required": "Indica el correo del cliente.",
                     "price_list_channel_required": "Selecciona un canal.",
                     "price_list_items_required": "Añade al menos un producto y precio.",
                     "invalid_price_list_item": "El producto o precio de la lista no es válido."})
    messages.update({"invalid_price_adjustment": "El ajuste porcentual no es válido.",
                     "invalid_sales_goal": "Completa correctamente vendedor, período, meta y comisión.",
                     "invalid_usability_feedback": "Califica la experiencia entre 1 y 5."})
    messages.update({"inventory_counts_required":"Añade al menos un conteo físico.","invalid_period":"El período debe tener formato AAAA-MM."})
    status = 404 if code == "not_found" else 409 if code == "already_decided" else 400
    return jsonify({"status": "error", "code": code, "message": messages.get(code, code)}), status


@profesional_bp.get("/resumen")
@login_required
def summary():
    return jsonify({"status": "ok", **services.professional_home(session.get("role"))})


@profesional_bp.get("/alertas")
@login_required
def alerts():
    return jsonify({"status": "ok", "items": services.action_alerts(int(request.args.get("threshold", 20)))})


@profesional_bp.get("/productos/<int:product_id>")
@login_required
def product(product_id: int):
    row = services.product_profile(product_id)
    return jsonify({"status": "ok", "profile": row}) if row else (jsonify({"status": "error", "message": "Producto no encontrado."}), 404)


@profesional_bp.get("/clientes/<int:client_id>")
@login_required
def customer(client_id: int):
    row = services.customer_profile(client_id)
    return jsonify({"status": "ok", "profile": row}) if row else (jsonify({"status": "error", "message": "Cliente no encontrado."}), 404)


@profesional_bp.get("/proveedores")
@login_required
def vendors():
    return jsonify({"status": "ok", "items": services.vendor_evaluation()})


@profesional_bp.route("/metas", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "GET":
        return jsonify({"status": "ok", "items": services.list_goals()})
    try:
        return jsonify({"status": "ok", "goal": services.create_goal(request.get_json(silent=True) or {}, session.get("email"))}), 201
    except ValueError as exc:
        return _error(exc)


@profesional_bp.route("/aprobaciones", methods=["GET", "POST"])
@login_required
def approvals():
    if request.method == "GET":
        return jsonify({"status": "ok", "items": services.list_approvals(request.args.get("status"))})
    try:
        return jsonify({"status": "ok", "approval": services.create_approval(request.get_json(silent=True) or {}, session.get("email"))}), 201
    except ValueError as exc:
        return _error(exc)


@profesional_bp.post("/aprobaciones/<int:approval_id>/decision")
@login_required
def approval_decision(approval_id: int):
    body = request.get_json(silent=True) or {}
    try:
        return jsonify({"status": "ok", "approval": services.decide_approval(approval_id, body.get("decision"), session.get("email"), str(body.get("comment") or ""))})
    except ValueError as exc:
        return _error(exc)


@profesional_bp.get("/historial")
@login_required
def history():
    return jsonify({"status": "ok", "items": services.readable_history(request.args.get("entity"), request.args.get("entity_id"), int(request.args.get("limit", 50)))})


@profesional_bp.get("/calidad")
@login_required
def quality():
    return jsonify({"status": "ok", "items": services.data_quality(), "validation": services.quality_issues()})


@profesional_bp.get("/operacion-avanzada")
@login_required
def advanced_operations():
    return jsonify({"status": "ok", "logistics": services.logistics_overview(),
                    "forecast": services.demand_forecast(), "profitability": services.profitability_summary(),
                    "loyalty": services.loyalty_overview(), "freshness": services.analytics_freshness(),
                    "comparisons": services.profitability_comparison()})


@profesional_bp.get("/clickhouse")
@login_required
def clickhouse_status():
    return jsonify({"status": "ok", **services.clickhouse_monitor()})


@profesional_bp.route("/lotes", methods=["GET", "POST"])
@permission_required("compras.manage")
def lots():
    if request.method == "GET":
        days = request.args.get("expiring_days", type=int)
        return jsonify({"status": "ok", **services.inventory_lot_overview(expiring_days=days)})
    try:
        row = services.save_inventory_lot(request.get_json(silent=True) or {}, session.get("email"))
        return jsonify({"status": "ok", "lot": row, "message": "Lote registrado con trazabilidad."}), 201
    except (TypeError, ValueError) as exc:
        return _error(exc if isinstance(exc, ValueError) else ValueError("invalid_lot"))


@profesional_bp.get("/lotes/<lot_code>/trazabilidad")
@permission_required("compras.manage")
def lot_trace(lot_code: str):
    try:
        return jsonify({"status": "ok", **services.lot_trace(lot_code)})
    except ValueError as exc:
        return _error(exc)


@profesional_bp.route("/listas-precios", methods=["GET", "POST"])
@permission_required("ventas.manage")
def price_lists():
    if request.method == "GET":
        return jsonify({"status": "ok", "items": services.price_lists_overview()})
    try:
        row = services.save_business_price_list(request.get_json(silent=True) or {}, session.get("email"))
        return jsonify({"status": "ok", "price_list": row, "message": "Lista de precios guardada."}), 201
    except (TypeError, ValueError) as exc:
        return _error(exc if isinstance(exc, ValueError) else ValueError("invalid_price_list"))


@profesional_bp.route("/vendedores", methods=["GET", "POST"])
@permission_required("ventas.manage")
def seller_performance():
    from shared.sales_performance import overview, save_goal
    if request.method == "GET":
        return jsonify({"status": "ok", "items": overview()})
    try:
        return jsonify({"status": "ok", "goal": save_goal(request.get_json(silent=True) or {}, session.get("email"))}), 201
    except (TypeError, ValueError) as exc:
        return _error(exc if isinstance(exc, ValueError) else ValueError("invalid_sales_goal"))


@profesional_bp.post("/usabilidad/opinion")
@login_required
def usability_feedback():
    from shared.sales_performance import save_usability_feedback
    try:
        return jsonify({"status": "ok", "feedback": save_usability_feedback(request.get_json(silent=True) or {}, session.get("email"))}), 201
    except (TypeError, ValueError) as exc:
        return _error(exc if isinstance(exc, ValueError) else ValueError("invalid_usability_feedback"))


@profesional_bp.route("/conciliacion-inventario",methods=["GET","POST"])
@permission_required("compras.manage")
def inventory_reconcile():
    if request.method=="GET": return jsonify({"status":"ok",**services.inventory_reconciliation()})
    try: return jsonify({"status":"ok",**services.apply_inventory_counts((request.get_json(silent=True) or {}).get("items") or [],session.get("email"))})
    except (TypeError,ValueError) as exc: return _error(exc if isinstance(exc,ValueError) else ValueError("inventory_counts_required"))


@profesional_bp.post("/cierre-mensual")
@permission_required("compras.manage")
def monthly_close():
    try: return jsonify({"status":"ok","close":services.monthly_management_close((request.get_json(silent=True) or {}).get("period"),session.get("email"))}),201
    except (TypeError,ValueError) as exc: return _error(exc if isinstance(exc,ValueError) else ValueError("invalid_period"))


@profesional_bp.get("/respaldos")
@permission_required("audit.read")
def backups(): return jsonify({"status":"ok","items":services.backup_catalog()})


@profesional_bp.post("/pronostico/requisicion")
@permission_required("compras.manage")
def forecast_requisition():
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_forecast_requisition(int(body.get("product_id") or 0), int(body.get("quantity") or 0))
        return jsonify({"status": "ok", "requisition": row, "message": "Requisición creada en borrador."}), 201
    except ValueError as exc:
        return _error(exc)


@profesional_bp.post("/fidelizacion/campana")
@permission_required("ventas.manage")
def loyalty_campaign():
    try:
        row = services.create_loyalty_campaign((request.get_json(silent=True) or {}).get("segment"), session.get("email"))
        return jsonify({"status": "ok", "campaign": row, "message": "Campaña creada."}), 201
    except ValueError as exc:
        return _error(exc)


@profesional_bp.get("/operacion-avanzada.pdf")
@permission_required("analysis.export")
def advanced_export_pdf():
    data = services.profitability_summary()
    rows = [{"concepto": key.replace("_", " ").title(), "monto": value}
            for key, value in data.items() if isinstance(value, (int, float))]
    from paquetes.reportes.pdf_export import generate_report_pdf
    content = generate_report_pdf(report_id="GESTIÓN", title="Operación avanzada",
        subtitle="Rentabilidad, logística, demanda y fidelización", columns=["concepto", "monto"], rows=rows)
    return Response(content, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=altavia-operacion-avanzada.pdf"})


@profesional_bp.patch("/logistica/<int:request_id>")
@permission_required("ventas.manage")
def shipment_update(request_id: int):
    try:
        row = services.update_shipment(request_id, request.get_json(silent=True) or {}, session.get("email"))
        return jsonify({"status": "ok", "shipment": row})
    except ValueError as exc:
        return _error(exc)


@profesional_bp.get("/buscar")
@login_required
def search():
    try:
        return jsonify({"status": "ok", "groups": services.global_search(request.args.get("q", ""), int(request.args.get("limit", 6)))})
    except ValueError as exc:
        return _error(exc)
