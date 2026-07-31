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
        "invalid_stock": ("Cantidad de stock inválida.", 400),
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
        if "delta" in body:
            row = services.add_stock(variant_id, int(body.get("delta") or 0))
        else:
            row = services.set_stock(variant_id, int(body.get("available") if "available" in body else body.get("inventory_quantity")))
        return jsonify({"status": "ok", "variant": row})
    except (TypeError, ValueError) as e:
        if isinstance(e, ValueError) and str(e) in ("invalid_variant",):
            return _err(e)
        return _err(ValueError("invalid_stock"))


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
