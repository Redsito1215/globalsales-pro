"""Rutas — compras, proveedores e inventario."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.compras import services

compras_bp = Blueprint("compras", __name__, url_prefix="/api/compras")


def _err(exc: ValueError):
    code = str(exc)
    messages = {
        "name_required": ("Nombre del proveedor obligatorio.", 400),
        "not_found": ("Registro no encontrado.", 404),
        "invalid_vendor": ("Proveedor no válido.", 400),
        "invalid_variant": ("Variante no encontrada.", 404),
        "invalid_line": ("Línea inválida.", 400),
        "lines_required": ("Indique al menos una línea.", 400),
        "po_closed": ("La orden ya está cerrada.", 409),
        "po_not_draft": ("Solo se puede enviar una OC en borrador.", 409),
        "po_not_sent": ("Envía la OC antes de recibir mercancía.", 409),
        "no_lines": ("La orden no tiene líneas.", 400),
        "nothing_to_receive": ("No hay cantidades pendientes por recibir.", 400),
        "invalid_country": ("País del proveedor no válido.", 400),
        "invalid_region": ("Continente del proveedor no válido.", 400),
        "req_not_draft": ("Solo se puede aprobar una requisición en borrador.", 409),
        "req_not_approved": ("Aprueba la requisición antes de generar la OC.", 409),
        "req_closed": ("La requisición ya está cerrada.", 409),
        "reason_required": ("Indique un motivo para esta acción.", 400),
        "reason_too_short": ("El motivo debe tener al menos 8 caracteres.", 400),
        "use_disable": ("Los proveedores no se eliminan; deben inhabilitarse.", 409),
        "duplicate_vendor": ("Ya existe un proveedor con ese nombre.", 409),
        "duplicate_vendor_email": ("Ya existe un proveedor con ese correo.", 409),
        "invalid_period": ("Período contable inválido.", 400),
        "period_already_closed": ("Ese período contable ya está cerrado.", 409),
        "accounting_period_closed": ("El período contable está cerrado y no admite movimientos.", 409),
        "invalid_amount": ("El monto debe ser mayor a cero.", 400),
        "credit_note_exceeds_paid": ("La nota de crédito supera el valor pagado disponible.", 409),
        "payment_exceeds_balance": ("El abono supera el saldo pendiente.", 409),
        "duplicate_payment_reference": ("Ya existe un abono con esa referencia.", 409),
        "reference_required": ("Indique una referencia de al menos 6 caracteres.", 400),
        "approval_required_for_payment": ("La solicitud debe estar aprobada antes del abono.", 409),
        "client_required": ("Indique el correo del cliente.", 400),
        "invalid_margin_group": ("Agrupación de margen no válida.", 400),
        "invalid_inventory_policy": ("El objetivo debe ser igual o mayor al mínimo.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status


@compras_bp.get("/vendors")
@login_required
@permission_required("compras.manage")
def vendors_list():
    active_only = request.args.get("active_only", "").lower() in ("1", "true", "yes")
    return jsonify({"status": "ok", "vendors": services.list_vendors(active_only=active_only)})


@compras_bp.post("/vendors")
@login_required
@permission_required("compras.manage")
def vendors_create():
    body = request.get_json(silent=True) or {}
    try:
        row = services.upsert_vendor(body)
        return jsonify({"status": "ok", "vendor": row}), 201
    except ValueError as e:
        return _err(e)


@compras_bp.put("/vendors/<int:vendor_id>")
@login_required
@permission_required("compras.manage")
def vendors_update(vendor_id: int):
    body = request.get_json(silent=True) or {}
    try:
        row = services.upsert_vendor(body, vendor_id=vendor_id)
        return jsonify({"status": "ok", "vendor": row})
    except ValueError as e:
        return _err(e)


@compras_bp.delete("/vendors/<int:vendor_id>")
@login_required
@permission_required("compras.manage")
def vendors_delete(vendor_id: int):
    try:
        services.delete_vendor(vendor_id)
        return jsonify({"status": "ok", "message": "Proveedor eliminado."})
    except ValueError as e:
        return _err(e)


@compras_bp.patch("/vendors/<int:vendor_id>/status")
@login_required
@permission_required("compras.manage")
def vendors_status(vendor_id: int):
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("active"), bool):
        return jsonify({"status": "error", "message": "Indique un estado válido.", "code": "invalid_active"}), 400
    try:
        row = services.set_vendor_active(vendor_id, body["active"], reason=body.get("reason"))
        msg = "Proveedor habilitado." if body["active"] else "Proveedor inhabilitado."
        return jsonify({"status": "ok", "message": msg, "vendor": row})
    except ValueError as e:
        return _err(e)


@compras_bp.get("/inventory")
@login_required
@permission_required("compras.manage")
def inventory_list():
    data = services.list_inventory(
        q=(request.args.get("q") or "").strip() or None,
        low_only=request.args.get("low_only", "").lower() in ("1", "true", "yes"),
        threshold=int(request.args.get("threshold", 20) or 20),
        limit=min(int(request.args.get("limit", 100)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@compras_bp.patch("/inventory/<int:variant_id>")
@login_required
@permission_required("compras.manage")
def inventory_set(variant_id: int):
    body = request.get_json(silent=True) or {}
    try:
        reason = services.normalize_adjustment_reason(body.get("reason"))
        if "delta" in body:
            row = services.add_stock(variant_id, int(body.get("delta") or 0), reason=reason)
        else:
            row = services.set_stock(
                variant_id,
                int(body.get("available") if "available" in body else body.get("inventory_quantity")),
                reason=reason,
            )
        return jsonify({"status": "ok", "variant": row})
    except (TypeError, ValueError) as e:
        if isinstance(e, ValueError) and str(e) in ("invalid_variant", "reason_required", "reason_too_short"):
            return _err(e)
        return _err(ValueError("invalid_stock"))


@compras_bp.get("/inventory/<int:variant_id>/kardex")
@login_required
@permission_required("compras.manage")
def inventory_kardex(variant_id: int):
    rows = services.list_kardex(variant_id, limit=min(int(request.args.get("limit", 100)), 500))
    return jsonify({"status": "ok", "movements": rows, "count": len(rows)})


@compras_bp.patch("/inventory/<int:variant_id>/policy")
@login_required
@permission_required("compras.manage")
def inventory_policy(variant_id: int):
    body = request.get_json(silent=True) or {}
    try:
        row = services.set_inventory_policy(
            variant_id, minimum=int(body.get("minimum")), target=int(body.get("target")),
        )
        return jsonify({"status": "ok", "policy": row, "message": "Política de reposición actualizada."})
    except (TypeError, ValueError) as exc:
        return _err(exc if isinstance(exc, ValueError) else ValueError("invalid_inventory_policy"))


@compras_bp.post("/inventory/<int:variant_id>/physical-count")
@login_required
@permission_required("compras.manage")
def inventory_physical_count(variant_id: int):
    body = request.get_json(silent=True) or {}
    try:
        row = services.register_physical_count(
            variant_id, counted=int(body.get("counted")), reason=body.get("reason") or "",
        )
        return jsonify({"status": "ok", "count": row, "message": "Conteo físico aplicado y registrado."}), 201
    except (TypeError, ValueError) as exc:
        return _err(exc if isinstance(exc, ValueError) else ValueError("invalid_stock"))


@compras_bp.get("/purchase-orders")
@login_required
@permission_required("compras.manage")
def po_list():
    status = (request.args.get("status") or "").strip() or None
    data = services.list_purchase_orders(
        status=status,
        limit=min(int(request.args.get("limit", 50)), 100),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@compras_bp.get("/purchase-orders/<int:po_id>")
@login_required
@permission_required("compras.manage")
def po_get(po_id: int):
    row = services.get_purchase_order(po_id)
    if not row:
        return jsonify({"status": "error", "message": "OC no encontrada.", "code": "not_found"}), 404
    return jsonify({"status": "ok", "order": row})


@compras_bp.post("/purchase-orders")
@login_required
@permission_required("compras.manage")
def po_create():
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_purchase_order(body)
        return jsonify({"status": "ok", "order": row}), 201
    except ValueError as e:
        return _err(e)


@compras_bp.post("/purchase-orders/<int:po_id>/send")
@login_required
@permission_required("compras.manage")
def po_send(po_id: int):
    try:
        row = services.send_purchase_order(po_id)
        return jsonify({"status": "ok", "order": row, "message": "OC enviada al proveedor."})
    except ValueError as e:
        return _err(e)


@compras_bp.post("/purchase-orders/<int:po_id>/receive")
@login_required
@permission_required("compras.manage")
def po_receive(po_id: int):
    body = request.get_json(silent=True) or {}
    try:
        row = services.receive_purchase_order(po_id, receipts=body.get("receipts"))
        return jsonify({"status": "ok", "order": row, "message": "Recepción aplicada al inventario."})
    except ValueError as e:
        return _err(e)


@compras_bp.post("/purchase-orders/<int:po_id>/cancel")
@login_required
@permission_required("compras.manage")
def po_cancel(po_id: int):
    try:
        row = services.cancel_purchase_order(po_id)
        return jsonify({"status": "ok", "order": row})
    except ValueError as e:
        return _err(e)


@compras_bp.get("/cash-ledger")
@login_required
@permission_required("compras.manage")
def cash_ledger_list():
    from shared.cash_ledger import list_cash_movements

    data = list_cash_movements(
        limit=min(int(request.args.get("limit", 50)), 200),
        movement_type=(request.args.get("type") or "").strip() or None,
        q=(request.args.get("q") or "").strip() or None,
    )
    return jsonify({"status": "ok", **data})


@compras_bp.get("/accounting/summary")
@login_required
@permission_required("compras.manage")
def accounting_summary():
    from shared.accounting import financial_summary

    return jsonify({"status": "ok", **financial_summary()})


@compras_bp.get("/accounting/receivables")
@login_required
@permission_required("compras.manage")
def accounting_receivables():
    from shared.accounting import list_receivables

    return jsonify({"status": "ok", **list_receivables(limit=min(int(request.args.get("limit", 100)), 500))})


@compras_bp.get("/accounting/customers/<path:email>/statement")
@login_required
@permission_required("compras.manage")
def accounting_customer_statement(email: str):
    from shared.accounting import customer_statement
    try:
        return jsonify({"status": "ok", **customer_statement(email, limit=min(int(request.args.get("limit", 200)), 500))})
    except ValueError as e:
        return _err(e)


@compras_bp.post("/accounting/receivables/<int:request_id>/payments")
@login_required
@permission_required("compras.manage")
def accounting_partial_payment(request_id: int):
    from flask import session
    from shared.accounting import record_partial_payment
    body = request.get_json(silent=True) or {}
    try:
        row = record_partial_payment(
            request_id, amount=float(body.get("amount") or 0), reference=body.get("reference") or "",
            actor_email=session.get("email"), payment_method=body.get("payment_method") or "tarjeta",
        )
        return jsonify({"status": "ok", "message": "Abono registrado correctamente.", **row}), 201
    except (TypeError, ValueError) as e:
        return _err(e if isinstance(e, ValueError) else ValueError("invalid_amount"))


@compras_bp.get("/accounting/margins")
@login_required
@permission_required("compras.manage")
def accounting_margins():
    from shared.accounting import margin_report
    try:
        return jsonify({"status": "ok", **margin_report(
            group_by=(request.args.get("group_by") or "product").strip(),
            limit=min(int(request.args.get("limit", 100)), 500),
        )})
    except ValueError as e:
        return _err(e)


@compras_bp.get("/accounting/reconciliation/<int:request_id>")
@login_required
@permission_required("compras.manage")
def accounting_reconciliation(request_id: int):
    from shared.accounting import reconcile_request

    try:
        return jsonify({"status": "ok", **reconcile_request(request_id)})
    except ValueError as e:
        return _err(e)


@compras_bp.get("/accounting/periods")
@login_required
@permission_required("compras.manage")
def accounting_periods():
    from shared.accounting import list_periods

    return jsonify({"status": "ok", "periods": list_periods()})


@compras_bp.post("/accounting/periods/close")
@login_required
@permission_required("compras.manage")
def accounting_close_period():
    from flask import session
    from shared.accounting import close_period

    body = request.get_json(silent=True) or {}
    try:
        row = close_period(
            period_type=body.get("period_type"), value=body.get("value"),
            reason=body.get("reason"), actor_email=session.get("email"),
        )
        return jsonify({"status": "ok", "message": "Período contable cerrado.", "period": row}), 201
    except ValueError as e:
        return _err(e)


@compras_bp.get("/accounting/credit-notes")
@login_required
@permission_required("compras.manage")
def accounting_credit_notes():
    from shared.accounting import list_credit_notes

    return jsonify({"status": "ok", "credit_notes": list_credit_notes()})


@compras_bp.post("/accounting/credit-notes")
@login_required
@permission_required("compras.manage")
def accounting_credit_note_create():
    from flask import session
    from shared.accounting import create_credit_note

    body = request.get_json(silent=True) or {}
    try:
        row = create_credit_note(
            request_id=int(body.get("request_id") or 0), amount=float(body.get("amount") or 0),
            reason=body.get("reason"), actor_email=session.get("email"), source="manual",
        )
        return jsonify({"status": "ok", "message": "Nota de crédito emitida.", "credit_note": row}), 201
    except (TypeError, ValueError) as e:
        return _err(e if isinstance(e, ValueError) else ValueError("invalid_amount"))


@compras_bp.get("/scrap")
@login_required
@permission_required("compras.manage")
def scrap_list():
    data = services.list_scrapped_inventory(
        limit=min(int(request.args.get("limit", 50)), 200),
        q=(request.args.get("q") or "").strip() or None,
    )
    return jsonify({"status": "ok", **data})


@compras_bp.get("/purchase-orders/<int:po_id>/historial")
@login_required
@permission_required("compras.manage")
def po_historial(po_id: int):
    from paquetes.datos.services import list_audit_for_entity

    data = list_audit_for_entity("purchase_orders", po_id, limit=25)
    return jsonify({"status": "ok", **data})


@compras_bp.get("/requisitions")
@login_required
@permission_required("compras.manage")
def requisitions_list():
    status = (request.args.get("status") or "").strip() or None
    data = services.list_purchase_requisitions(
        status=status,
        limit=min(int(request.args.get("limit", 50)), 100),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@compras_bp.post("/requisitions")
@login_required
@permission_required("compras.manage")
def requisitions_create():
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_purchase_requisition(body)
        return jsonify({"status": "ok", "requisition": row, "message": "Requisición creada en borrador."}), 201
    except ValueError as e:
        return _err(e)


@compras_bp.get("/requisitions/<int:req_id>")
@login_required
@permission_required("compras.manage")
def requisitions_get(req_id: int):
    row = services.get_purchase_requisition(req_id)
    if not row:
        return _err(ValueError("not_found"))
    return jsonify({"status": "ok", "requisition": row})


@compras_bp.post("/requisitions/<int:req_id>/aprobar")
@login_required
@permission_required("compras.manage")
def requisitions_approve(req_id: int):
    try:
        row = services.approve_purchase_requisition(req_id)
        return jsonify({"status": "ok", "requisition": row, "message": "Requisición aprobada."})
    except ValueError as e:
        return _err(e)


@compras_bp.post("/requisitions/<int:req_id>/convertir-oc")
@login_required
@permission_required("compras.manage")
def requisitions_convert(req_id: int):
    try:
        result = services.convert_requisition_to_po(req_id)
        return jsonify(
            {
                "status": "ok",
                **result,
                "message": f"OC #{result['purchase_order'].get('po_id')} creada en borrador.",
            }
        )
    except ValueError as e:
        return _err(e)


@compras_bp.post("/requisitions/<int:req_id>/cancelar")
@login_required
@permission_required("compras.manage")
def requisitions_cancel(req_id: int):
    try:
        row = services.cancel_purchase_requisition(req_id)
        return jsonify({"status": "ok", "requisition": row})
    except ValueError as e:
        return _err(e)
