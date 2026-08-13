"""Rutas tienda — storefront tipo Shopify."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from auth.decorators import login_required, permission_required
from paquetes.shop import services

shop_bp = Blueprint("shop", __name__, url_prefix="/api/shop")


@shop_bp.get("/collections")
def shop_collections():
    return jsonify({"status": "ok", "collections": services.list_collections_public()})


@shop_bp.get("/products")
def shop_products():
    cid = request.args.get("collection_id", type=int)
    data = services.list_products_shop(
        collection_id=cid,
        limit=min(int(request.args.get("limit", 48)), 100),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@shop_bp.get("/products/<int:product_id>")
def shop_product_detail(product_id: int):
    row = services.get_product_shop(product_id)
    if not row:
        return jsonify({"status": "error", "message": "Producto no encontrado.", "code": "not_found"}), 404
    return jsonify({"status": "ok", "product": row})


@shop_bp.get("/countries")
def shop_countries():
    from shared.checkout_countries import list_checkout_countries

    data = list_checkout_countries(limit=min(int(request.args.get("limit", 500)), 500))
    return jsonify({"status": "ok", **data})


@shop_bp.post("/coupon/validate")
def shop_validate_coupon():
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or "").strip()
    subtotal = float(body.get("subtotal") or 0)
    try:
        data = services.validate_coupon(code, subtotal)
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        code = str(e)
        msg = {
            "invalid_coupon": "Cupón no válido.",
            "coupon_exhausted": "Cupón agotado.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@shop_bp.post("/shipping/quote")
def shop_shipping_quote():
    body = request.get_json(silent=True) or {}
    try:
        data = services.quote_shipping(body)
        return jsonify(data)
    except ValueError as e:
        code = str(e)
        msg = {
            "lines_required": "Agrega productos al carrito.",
            "invalid_country": "Selecciona un país de destino.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@shop_bp.post("/checkout")
@login_required
@permission_required("shop.checkout")
def shop_checkout():
    body = request.get_json(silent=True) or {}
    role = session.get("role")
    assisted = (role or "") != "cliente"
    # Cliente: siempre su cuenta. Vendedor/admin: puede pedir para un cliente fijo.
    if assisted:
        client_email = (body.get("client_email") or body.get("email") or session.get("email") or "").strip()
        client_name = (body.get("client_name") or body.get("name") or session.get("name") or "Cliente").strip()
    else:
        client_email = (session.get("email") or "").strip()
        client_name = (session.get("name") or body.get("name") or "Cliente").strip()
    body = {
        **body,
        "email": client_email,
        "name": client_name,
        "client_email": client_email,
        "client_name": client_name,
    }
    try:
        result = services.create_checkout_from_cart(body)
        return jsonify({"status": "ok", "message": "Solicitud de compra registrada.", **result}), 201
    except ValueError as e:
        code = str(e)
        msg = {
            "lines_required": "Agrega productos al carrito.",
            "invalid_variant": "Producto no válido.",
            "insufficient_stock": "Stock insuficiente para uno o más productos.",
            "invalid_coupon": "Cupón no válido.",
            "coupon_exhausted": "Este cupón ya no tiene usos disponibles.",
            "client_required": "Inicia sesión para completar la compra.",
            "destination_required": "Indica el destino de entrega (ciudad, dirección o ruta).",
            "invalid_quantity": "Cada producto debe tener al menos 1 unidad.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@shop_bp.post("/sync")
@login_required
@permission_required("masters.write")
def shop_sync():
    body = request.get_json(silent=True) or {}
    reset_stock = bool(body.get("reset_stock")) or request.args.get("reset_stock", "").lower() in (
        "1",
        "true",
        "yes",
    )
    counts = services.sync_from_masters(reset_stock=reset_stock)
    msg = (
        "Catálogo regenerado (stock reiniciado desde maestros)."
        if reset_stock
        else "Catálogo sincronizado (stock existente conservado)."
    )
    return jsonify({"status": "ok", "message": msg, "counts": counts, "reset_stock": reset_stock})


@shop_bp.patch("/variants/<int:variant_id>/stock")
@login_required
@permission_required("compras.manage")
def shop_adjust_stock(variant_id: int):
    body = request.get_json(silent=True) or {}
    try:
        available = int(body.get("available") if "available" in body else body.get("inventory_quantity"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Indica las existencias disponibles (número entero).", "code": "invalid_stock"}), 400
    try:
        row = services.adjust_variant_stock(variant_id, available)
        return jsonify({"status": "ok", "variant": row})
    except ValueError as e:
        code = str(e)
        msg = {"invalid_variant": "Variante no encontrada."}.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 404


@shop_bp.get("/stats")
def shop_stats():
    return jsonify({"status": "ok", "counts": services.shop_table_counts()})
