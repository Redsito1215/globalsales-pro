"""Rutas tienda — storefront tipo Shopify."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import admin_required
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


@shop_bp.post("/checkout")
def shop_checkout():
    body = request.get_json(silent=True) or {}
    try:
        result = services.create_checkout_from_cart(body)
        return jsonify({"status": "ok", "message": "Checkout registrado.", **result}), 201
    except ValueError as e:
        code = str(e)
        msg = {
            "lines_required": "Agrega productos al carrito.",
            "invalid_variant": "Producto no válido.",
            "insufficient_stock": "Stock insuficiente para uno o más productos.",
            "invalid_coupon": "Cupón no válido.",
            "coupon_exhausted": "Este cupón ya no tiene usos disponibles.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@shop_bp.post("/sync")
@admin_required
def shop_sync():
    counts = services.sync_from_masters()
    return jsonify({"status": "ok", "message": "Catálogo Shopify sincronizado desde maestros.", "counts": counts})


@shop_bp.get("/stats")
def shop_stats():
    return jsonify({"status": "ok", "counts": services.shop_table_counts()})
