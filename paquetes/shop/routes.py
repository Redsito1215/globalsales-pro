"""Rutas tienda — storefront tipo Shopify."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from auth.decorators import admin_required, login_required, permission_required
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
        limit=min(max(int(request.args.get("limit", 48)), 1), 200),
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
        data = services.validate_coupon(code, subtotal, customer_email=session.get("email"))
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        code = str(e)
        if code.startswith("commercial_exception_required:"):
            return jsonify({
                "status": "error", "message": "El pedido supera una política comercial o queda bajo el margen mínimo. Requiere autorización administrativa.",
                "code": "commercial_exception_required", "violations": code.split(":", 1)[1].split(","),
            }), 409
        msg = {
            "invalid_coupon": "Cupón no válido.",
            "coupon_exhausted": "Cupón agotado.",
            "coupon_not_current": "El cupón todavía no inicia o ya venció.",
            "coupon_minimum_order": "El pedido no alcanza el monto mínimo del cupón.",
            "coupon_segment_restricted": "Este cupón no está disponible para tu segmento de cliente.",
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
        if code.startswith("commercial_exception_required:"):
            return jsonify({
                "status": "error",
                "message": "El pedido requiere autorización por las políticas comerciales configuradas.",
                "code": "commercial_exception_required",
                "violations": code.split(":", 1)[1].split(","),
            }), 409
        msg = {
            "lines_required": "Agrega productos al carrito.",
            "invalid_variant": "Producto no válido.",
            "insufficient_stock": "Stock insuficiente para uno o más productos.",
            "invalid_coupon": "Cupón no válido.",
            "coupon_exhausted": "Este cupón ya no tiene usos disponibles.",
            "coupon_not_current": "El cupón todavía no inicia o ya venció.",
            "coupon_minimum_order": "El pedido no alcanza el monto mínimo del cupón.",
            "coupon_segment_restricted": "Este cupón no está disponible para este cliente.",
            "client_required": "Inicia sesión para completar la compra.",
            "destination_required": "Indica el destino de entrega (ciudad, dirección o ruta).",
            "invalid_quantity": "Cada producto debe tener al menos 1 unidad.",
            "invalid_phone": "El teléfono no puede ser negativo ni contener solo signos.",
            "invalid_unit_price": "El precio debe ser mayor a 0.",
            "invalid_unit_cost": "El costo no puede ser negativo.",
            "invalid_discount_amount": "El descuento no puede ser negativo.",
            "invalid_shipping_cost": "El envío no puede ser negativo.",
            "invalid_total": "El total no puede ser negativo.",
            "invalid_subtotal": "El subtotal no puede ser negativo.",
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


@shop_bp.patch("/products/<int:product_id>/sale")
@login_required
@permission_required("masters.write")
def shop_product_sale(product_id: int):
    body = request.get_json(silent=True) or {}
    if "enabled" not in body:
        return jsonify(
            {"status": "error", "message": "Indica si la rebaja debe activarse.", "code": "enabled_required"}
        ), 400
    enabled = bool(body.get("enabled"))
    percent = body.get("percent") if "percent" in body else body.get("sale_percent")
    try:
        pct_arg = None if percent is None or percent == "" else int(percent)
    except (TypeError, ValueError):
        return jsonify(
            {"status": "error", "message": "El porcentaje de rebaja debe ser un número entre 1 y 90.", "code": "invalid_percent"}
        ), 400
    try:
        data = services.set_product_sale(product_id, enabled, sale_percent=pct_arg)
    except ValueError as exc:
        if str(exc) == "not_found":
            return jsonify({"status": "error", "message": "Producto no encontrado.", "code": "not_found"}), 404
        raise
    pct = data.get("sale_percent", services.STORE_SALE_PERCENT)
    msg = (
        f"Rebaja del {pct}% activada para este producto."
        if enabled
        else "Rebaja desactivada para este producto."
    )
    return jsonify({"status": "ok", "message": msg, **data})


@shop_bp.patch("/categories/<int:category_id>/sale")
@login_required
@permission_required("masters.write")
def shop_category_sale(category_id: int):
    body = request.get_json(silent=True) or {}
    if "enabled" not in body:
        return jsonify({"status": "error", "message": "Indica si la rebaja debe activarse."}), 400
    try:
        percent = int(body.get("percent", body.get("sale_percent", 25)))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "El porcentaje debe ser un número entre 1 y 90."}), 400
    try:
        data = services.set_category_sale(category_id, bool(body.get("enabled")), percent)
    except ValueError as exc:
        if str(exc) == "not_found":
            return jsonify({"status": "error", "message": "Categoría no encontrada."}), 404
        raise
    action = "activada" if data["sale_enabled"] else "desactivada"
    return jsonify({
        "status": "ok",
        "message": f"Rebaja del {data['sale_percent']}% {action} en {data['products_updated']} productos.",
        **data,
    })


@shop_bp.get("/stats")
def shop_stats():
    return jsonify({"status": "ok", "counts": services.shop_table_counts()})


@shop_bp.get("/commercial/settings")
@admin_required
def commercial_settings_get():
    from shared.commercial import commercial_settings
    return jsonify({"status": "ok", "settings": commercial_settings()})


@shop_bp.patch("/commercial/settings")
@admin_required
def commercial_settings_patch():
    from shared.commercial import update_commercial_settings
    try:
        row = update_commercial_settings(request.get_json(silent=True) or {}, actor_email=session.get("email"))
        return jsonify({"status": "ok", "message": "Políticas comerciales actualizadas.", "settings": row})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": "Valores comerciales no válidos.", "code": str(exc)}), 400


@shop_bp.get("/products/<int:product_id>/price-history")
@admin_required
def commercial_price_history(product_id: int):
    from shared.commercial import list_price_history
    rows = list_price_history(product_id, limit=min(int(request.args.get("limit", 100)), 500))
    return jsonify({"status": "ok", "history": rows, "count": len(rows)})


@shop_bp.get("/commercial/discounts")
@admin_required
def commercial_discounts_get():
    from shared.commercial import list_discounts
    rows = list_discounts(include_inactive=request.args.get("active_only") != "1")
    return jsonify({"status": "ok", "discounts": rows, "count": len(rows)})


@shop_bp.post("/commercial/discounts")
@admin_required
def commercial_discounts_save():
    from shared.commercial import save_discount
    try:
        row = save_discount(request.get_json(silent=True) or {}, actor_email=session.get("email"))
        return jsonify({"status": "ok", "message": "Descuento y vigencia guardados.", "discount": row})
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": "Datos del descuento no válidos.", "code": str(exc)}), 400


@shop_bp.get("/commercial/exceptions")
@admin_required
def commercial_exceptions_get():
    from shared.commercial import list_exceptions
    rows = list_exceptions(status=request.args.get("status"), limit=int(request.args.get("limit", 200)))
    return jsonify({"status": "ok", "exceptions": rows, "count": len(rows)})


@shop_bp.patch("/products/<int:product_id>/featured")
@admin_required
def commercial_product_featured(product_id: int):
    from shared.commercial import set_product_featured
    try:
        row = set_product_featured(product_id, bool((request.get_json(silent=True) or {}).get("featured")), actor_email=session.get("email"))
        return jsonify({"status": "ok", "message": "Producto destacado actualizado.", "product": row})
    except ValueError:
        return jsonify({"status": "error", "message": "Producto no encontrado.", "code": "not_found"}), 404


@shop_bp.post("/commercial/segments/refresh")
@admin_required
def commercial_segments_refresh():
    from shared.commercial import refresh_customer_segments
    rows = refresh_customer_segments(limit=min(int((request.get_json(silent=True) or {}).get("limit", 1000)), 5000))
    return jsonify({"status": "ok", "message": "Segmentación actualizada.", "customers": rows, "count": len(rows)})


@shop_bp.patch("/commercial/customers/<path:email>")
@admin_required
def commercial_customer_terms(email: str):
    from shared.commercial import update_customer_terms
    try:
        row = update_customer_terms(email, request.get_json(silent=True) or {}, actor_email=session.get("email"))
        return jsonify({"status": "ok", "message": "Condiciones del cliente actualizadas.", "customer": row})
    except ValueError as exc:
        status = 404 if str(exc) == "customer_not_found" else 400
        return jsonify({"status": "error", "message": "Condiciones del cliente no válidas.", "code": str(exc)}), status


@shop_bp.post("/commercial/exceptions")
@login_required
@permission_required("ventas.manage")
def commercial_exception_create():
    from shared.commercial import create_exception
    try:
        row = create_exception(request.get_json(silent=True) or {}, actor_email=session.get("email"))
        return jsonify({"status": "ok", "message": "Excepción enviada para autorización.", "exception": row}), 201
    except ValueError as exc:
        return jsonify({"status": "error", "message": "Indica un motivo válido.", "code": str(exc)}), 400


@shop_bp.post("/commercial/exceptions/<int:exception_id>/decision")
@admin_required
def commercial_exception_decide(exception_id: int):
    from shared.commercial import decide_exception
    body = request.get_json(silent=True) or {}
    try:
        row = decide_exception(
            exception_id, approved=bool(body.get("approved")), actor_email=session.get("email"), reason=body.get("reason") or "",
        )
        return jsonify({"status": "ok", "message": "Excepción resuelta.", "exception": row})
    except ValueError as exc:
        return jsonify({"status": "error", "message": "No se pudo resolver la excepción.", "code": str(exc)}), 409
