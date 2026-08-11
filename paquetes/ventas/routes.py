"""Rutas Flask — paquete Q3 Ventas."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from auth import roles_service
from auth.decorators import admin_required, login_required, permission_required
from paquetes.tablero import queries
from paquetes.ventas import services

ventas_bp = Blueprint("ventas", __name__, url_prefix="/api")


def _can_read_solicitudes(role: str | None) -> bool:
    return (
        role == "administrador"
        or roles_service.has_permission(role, "ventas.manage")
        or roles_service.has_permission(role, "orders.read")
    )


def _can_manage_solicitudes(role: str | None) -> bool:
    return role == "administrador" or roles_service.has_permission(role, "ventas.manage")


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
@login_required
@permission_required("orders.read")
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
@login_required
@permission_required("shop.checkout")
def crear_solicitud():
    """Deprecated: el alta con stock va por vitrina (`POST /api/shop/checkout`)."""
    return jsonify(
        {
            "status": "error",
            "message": "Usa la Vitrina B2B (checkout) para crear pedidos con control de stock.",
            "code": "use_checkout",
        }
    ), 400


@ventas_bp.get("/solicitudes")
@login_required
def listar_solicitudes():
    role = session.get("role")
    if not _can_read_solicitudes(role):
        return jsonify({"status": "error", "message": "No tienes permiso para esta acción.", "code": "forbidden"}), 403
    status = (request.args.get("status") or "").strip() or None
    active_only = request.args.get("active_only", "").lower() in ("1", "true", "yes")
    if status == "activas":
        status = None
        active_only = True
    data = services.list_requests(
        status=status,
        active_only=active_only,
        q=(request.args.get("q") or "").strip() or None,
        limit=min(int(request.args.get("limit", 50)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    data["can_manage"] = _can_manage_solicitudes(role)
    return jsonify({"status": "ok", **data})


@ventas_bp.get("/solicitudes/pendientes/count")
@login_required
def count_pendientes():
    if not _can_read_solicitudes(session.get("role")):
        return jsonify({"status": "error", "message": "No tienes permiso para esta acción.", "code": "forbidden"}), 403
    return jsonify({"status": "ok", "pending": services.count_pending_requests()})


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
    if role not in ("administrador", "vendedor") and not roles_service.has_permission(
        role, "ventas.manage"
    ) and not roles_service.has_permission(role, "orders.read"):
        if (req.get("client_email") or "").lower() != email:
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


@ventas_bp.patch("/solicitudes/<int:request_id>/pago")
@permission_required("ventas.manage")
def cambiar_pago(request_id: int):
    """Staff: solo crédito comercial. El estado «pagado» lo marca el cliente con /pagar."""
    body = request.get_json(silent=True) or {}
    payment_status = (body.get("payment_status") or "").strip()
    if payment_status == "pagado":
        return jsonify(
            {
                "status": "error",
                "message": "Solo el cliente puede marcar el pedido como pagado (Mis pedidos → Pagar).",
                "code": "client_must_pay",
            }
        ), 409
    try:
        req = services.update_payment(
            request_id,
            payment_status,
            reviewer_email=session.get("email"),
            payment_method=body.get("payment_method"),
        )
        return jsonify({"status": "ok", "request": req})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.post("/solicitudes/<int:request_id>/pagar")
@login_required
def cliente_pagar(request_id: int):
    """Pago del cliente dueño de la solicitud (simulado)."""
    body = request.get_json(silent=True) or {}
    try:
        req = services.client_pay(
            request_id,
            client_email=session.get("email") or "",
            method=(body.get("method") or body.get("payment_method") or "tarjeta"),
        )
        return jsonify({"status": "ok", "message": "Pago registrado.", "request": req})
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.post("/solicitudes/<int:request_id>/registrar-pago")
@permission_required("ventas.manage")
def staff_registrar_pago(request_id: int):
    """Staff registra pago presencial o cuando el correo del cliente no tiene cuenta."""
    body = request.get_json(silent=True) or {}
    try:
        req = services.staff_register_payment(
            request_id,
            staff_email=session.get("email") or "",
            method=(body.get("method") or body.get("payment_method") or "tarjeta"),
        )
        return jsonify({"status": "ok", "message": "Pago registrado por el vendedor.", "request": req})
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
        hint = result.get("message_analytics") or ""
        return jsonify(
            {
                "status": "ok",
                "message": (
                    "Solicitud convertida en venta (capa landing). " + hint
                    if result.get("analytics_stale")
                    else "Solicitud convertida en venta."
                ),
                **result,
            }
        )
    except ValueError as e:
        return _ventas_error(e)


@ventas_bp.post("/solicitudes/<int:request_id>/devolver")
@permission_required("ventas.manage")
def devolver_solicitud(request_id: int):
    body = request.get_json(silent=True) or {}
    try:
        req = services.return_delivered_request(
            request_id,
            reviewer_email=session.get("email"),
            reason=body.get("reason"),
            condition=body.get("condition"),
            inspections=body.get("inspections") or body.get("lines"),
        )
        restock_u = int(req.get("return_restock_units") or 0)
        damaged_u = int(req.get("return_damaged_units") or 0)
        msg = (
            f"Devolución registrada. Reingresan a stock: {restock_u} ud(s). "
            f"Dañadas (no reingresan): {damaged_u} ud(s)."
        )
        return jsonify({"status": "ok", "message": msg, "request": req})
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
        "invalid_payment_method": (
            "Método de pago no válido para este canal.",
            400,
        ),
        "cannot_pay_closed": ("No se puede registrar pago en una solicitud cerrada.", 409),
        "already_paid": ("Esta solicitud ya está pagada.", 409),
        "client_must_pay": ("Solo el cliente puede marcar el pedido como pagado.", 409),
        "payment_required": (
            "En pedidos online el cliente debe pagar antes de enviar. "
            "En venta presencial puedes registrar crédito.",
            409,
        ),
        "payment_required_before_convert": (
            "En pedidos online el cliente debe pagar primero (Mis pedidos → Pagar). "
            "En venta presencial puedes registrar crédito.",
            409,
        ),
        "credit_offline_only": (
            "El crédito comercial solo aplica a ventas presenciales (Offline). "
            "En online el cliente debe pagar en Mis pedidos.",
            409,
        ),
        "already_converted": ("La solicitud ya fue convertida.", 409),
        "already_rejected": ("La solicitud ya fue rechazada.", 409),
        "already_delivered": ("La solicitud ya fue entregada.", 409),
        "already_returned": ("La solicitud ya fue devuelta.", 409),
        "must_be_delivered": ("Solo se pueden devolver pedidos entregados.", 409),
        "return_condition_required": (
            "Indica la condición del producto: apto, dañado o mixto.",
            400,
        ),
        "return_inspection_required": (
            "En devolución mixta debes inspeccionar cada línea (apto vs dañado).",
            400,
        ),
        "return_inspection_incomplete": (
            "Falta inspeccionar todas las líneas del pedido.",
            400,
        ),
        "return_qty_mismatch": (
            "Apto + dañado debe coincidir con la cantidad de cada línea.",
            400,
        ),
        "invalid_return_line": ("Línea de inspección no válida.", 400),
        "duplicate_return_line": ("Hay líneas de inspección duplicadas.", 400),
        "invalid_return_qty": ("Cantidades de inspección inválidas.", 400),
        "cannot_reject_approved": ("No se puede rechazar una solicitud aprobada.", 409),
        "approval_required": ("Debes aprobar la solicitud antes de convertirla.", 409),
        "must_convert_first": ("Primero convierte la solicitud en venta.", 409),
        "must_ship_first": ("Marca el pedido como enviado antes de entregarlo.", 409),
        "offline_no_shipping": ("Las ventas Offline no requieren confirmar envío.", 409),
        "invalid_transition": ("Transición de estado no permitida.", 409),
        "use_dedicated_endpoint": (
            "Usa el endpoint dedicado (convertir, devolver o cancelar).",
            409,
        ),
        "use_checkout": ("Usa la Vitrina B2B para crear el pedido.", 400),
        "cancelled": ("No se puede convertir una solicitud cancelada.", 409),
        "forbidden": ("No autorizado para esta solicitud.", 403),
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
