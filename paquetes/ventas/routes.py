"""Rutas Flask — paquete Q3 Ventas."""
from __future__ import annotations

import re

from flask import Blueprint, jsonify, request, session

from auth.decorators import admin_required, login_required, permission_required
from paquetes.tablero import queries
from paquetes.ventas import services

ventas_bp = Blueprint("ventas", __name__, url_prefix="/api")


@ventas_bp.get("/sales/orders")
@login_required
@permission_required("orders.read")
def sales_orders_list():
    return jsonify(
        queries.search_orders(
            country=request.args.get("country"),
            item_type=request.args.get("item_type"),
            channel=request.args.get("channel"),
            priority=request.args.get("priority"),
            region=request.args.get("region"),
            limit=int(request.args.get("limit", 50)),
            offset=int(request.args.get("offset", 0)),
        )
    )


@ventas_bp.get("/sales/orders/<order_id>")
def sales_orders_detail(order_id: str):
    order = services.get_order(order_id)
    if not order:
        return jsonify({"status": "error", "message": "Pedido no encontrado."}), 404
    return jsonify({"status": "ok", **order})


@ventas_bp.post("/sales/orders")
@admin_required
def sales_orders_create():
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_order(body)
        return jsonify({"status": "ok", "order": row}), 201
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.put("/sales/orders/<order_id>")
@admin_required
def sales_orders_update(order_id: str):
    body = request.get_json(silent=True) or {}
    try:
        row = services.update_order(order_id, body)
        return jsonify({"status": "ok", "order": row})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.delete("/sales/orders/<order_id>")
@admin_required
def sales_orders_delete(order_id: str):
    try:
        n = services.delete_order(order_id)
        return jsonify({"status": "ok", "message": f"Eliminados {n} registro(s).", "deleted": n})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.get("/tienda/productos")
def tienda_productos():
    cid = request.args.get("category_id", type=int)
    data = services.list_store_products(
        category_id=cid,
        limit=min(int(request.args.get("limit", 100)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@ventas_bp.post("/solicitudes")
def crear_solicitud():
    body = request.get_json(silent=True) or {}
    try:
        req = services.create_request(body)
        return jsonify({"status": "ok", "message": "Solicitud registrada.", "request": req}), 201
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.get("/solicitudes")
@login_required
@permission_required("ventas.manage")
def listar_solicitudes():
    status = (request.args.get("status") or "").strip() or None
    active_only = request.args.get("active_only", "").lower() in ("1", "true", "yes")
    if status == "activas":
        status = None
        active_only = True
    data = services.list_requests(
        status=status,
        active_only=active_only,
        limit=min(int(request.args.get("limit", 50)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@ventas_bp.get("/solicitudes/mias")
@login_required
def mis_solicitudes():
    email = (session.get("email") or "").strip()
    if not email:
        return jsonify({"status": "error", "message": "Sesión inválida."}), 401
    data = services.list_requests_for_email(
        email,
        limit=min(int(request.args.get("limit", 50)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@ventas_bp.get("/solicitudes/<int:request_id>")
@login_required
def obtener_solicitud(request_id: int):
    req = services.get_request(request_id)
    if not req:
        return jsonify({"status": "error", "message": "Solicitud no encontrada."}), 404
    email = (session.get("email") or "").strip().lower()
    role = session.get("role")
    if role not in ("administrador", "vendedor") and (req.get("client_email") or "").lower() != email:
        return jsonify({"status": "error", "message": "No autorizado."}), 403
    return jsonify({"status": "ok", "request": req})


@ventas_bp.post("/solicitudes/<int:request_id>/cancelar")
@login_required
def cancelar_solicitud(request_id: int):
    try:
        req = services.cancel_request_by_client(request_id, client_email=session.get("email") or "")
        return jsonify({"status": "ok", "message": "Solicitud cancelada.", "request": req})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.patch("/solicitudes/<int:request_id>/estado")
@permission_required("ventas.manage")
def cambiar_estado(request_id: int):
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip()
    try:
        req = services.update_status(request_id, status, reviewer_email=session.get("email"))
        return jsonify({"status": "ok", "request": req})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.post("/solicitudes/<int:request_id>/convertir")
@permission_required("ventas.manage")
def convertir_solicitud(request_id: int):
    try:
        result = services.convert_to_sale(
            request_id,
            admin_email=session.get("email"),
            actor_role=session.get("role"),
        )
        return jsonify({"status": "ok", "message": "Solicitud convertida en venta.", **result})
    except ValueError as e:
        return _ventas_error(e)


def _ventas_error(exc: ValueError):
    code = str(exc)
    messages = {
        "lines_required": ("Indique al menos un producto.", 400),
        "client_required": ("Nombre y correo del cliente son obligatorios.", 400),
        "invalid_country": ("País no válido.", 400),
        "invalid_channel": ("Canal no válido.", 400),
        "invalid_line": ("Línea de producto inválida.", 400),
        "invalid_product": ("Producto no encontrado en catálogo.", 404),
        "not_found": ("Solicitud no encontrada.", 404),
        "invalid_status": ("Estado no válido.", 400),
        "already_converted": ("La solicitud ya fue convertida.", 409),
        "already_rejected": ("La solicitud ya fue rechazada.", 409),
        "cannot_reject_approved": ("No se puede rechazar una solicitud aprobada.", 409),
        "approval_required": ("Debes aprobar la solicitud antes de convertirla.", 409),
        "cancelled": ("No se puede convertir una solicitud cancelada.", 409),
        "forbidden": ("No puedes cancelar esta solicitud.", 403),
        "cannot_cancel": ("Esta solicitud ya no se puede cancelar.", 409),
        "cannot_cancel_approved": ("No puedes cancelar una solicitud ya aprobada.", 409),
        "already_cancelled": ("La solicitud ya fue cancelada.", 409),
        "rejected": ("No se puede convertir una solicitud rechazada.", 409),
        "invalid_master_refs": ("Faltan datos maestros (país/región/canal).", 409),
        "no_lines": ("La solicitud no tiene líneas válidas.", 400),
        "fields_required": ("Complete región, país, producto y canal.", 400),
        "invalid_region": ("Región no existe en maestros.", 400),
        "invalid_units": ("Unidades debe ser mayor a 0.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status
