"""Rutas Flask — paquete Q1 Tablero."""
from flask import Blueprint, jsonify, request

from auth.decorators import admin_required
from config.settings import settings
from paquetes.tablero import catalogo, generar_ventas, queries

tablero_bp = Blueprint("tablero", __name__, url_prefix="/api")


def _normalize_months(raw: str | None) -> int | None:
    if raw is None or str(raw).strip() == "":
        return 24
    try:
        months = int(raw)
    except (TypeError, ValueError):
        return 24
    if months < 1:
        return 24
    return min(months, 999)


def _filters_from_request():
    months = _normalize_months(request.args.get("months"))
    return {
        "region": request.args.get("region") or None,
        "item_type": request.args.get("item_type") or None,
        "channel": request.args.get("channel") or None,
        "priority": request.args.get("priority") or None,
        "months": months,
    }


@tablero_bp.get("/health")
def health():
    ok = queries.ping_mongo()
    return jsonify(
        {
            "status": "ok" if ok else "error",
            "mongo_db": settings.mongo_db,
            "paquete": "q1_tablero",
        }
    ), (200 if ok else 503)


@tablero_bp.get("/summary")
def summary():
    return jsonify(queries.get_summary(**_filters_from_request()))


@tablero_bp.get("/regions")
def regions():
    return jsonify(queries.revenue_by_region(**_filters_from_request()))


@tablero_bp.get("/products")
def products():
    return jsonify(queries.revenue_by_product(**_filters_from_request()))


@tablero_bp.get("/catalog/categories")
def catalog_categories():
    return jsonify(catalogo.list_categories())


@tablero_bp.get("/catalog/products")
def catalog_products():
    cid = request.args.get("category_id", type=int)
    if cid is None:
        return jsonify(
            {
                "status": "error",
                "message": "Parámetro category_id obligatorio (1–12).",
                "catalog_version": catalogo.CATALOG_VERSION,
            }
        ), 400
    return jsonify(
        catalogo.list_products_for_category(
            cid,
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0)),
        )
    )


@tablero_bp.post("/catalog/sync")
@admin_required
def catalog_sync():
    """Regenera dim_categoria + dim_producto (120 SKUs, 10 por categoría)."""
    try:
        return jsonify({"status": "ok", **catalogo.sync_products_to_mongo()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tablero_bp.get("/trend")
def trend():
    f = _filters_from_request()
    months = int(request.args.get("months", f.get("months") or 24))
    return jsonify(queries.monthly_trend(months, **f))


@tablero_bp.get("/channels")
def channels():
    return jsonify(queries.channel_breakdown(**_filters_from_request()))


@tablero_bp.get("/priorities")
def priorities():
    return jsonify(queries.priority_breakdown(**_filters_from_request()))


@tablero_bp.get("/countries")
def countries():
    f = _filters_from_request()
    top = int(request.args.get("top", 10))
    return jsonify(queries.top_countries(top, **f))


@tablero_bp.get("/orders")
def orders():
    f = _filters_from_request()
    return jsonify(
        queries.search_orders(
            country=request.args.get("country"),
            item_type=f.get("item_type"),
            channel=f.get("channel"),
            priority=f.get("priority"),
            region=f.get("region"),
            months=f.get("months"),
            limit=int(request.args.get("limit", 50)),
            offset=int(request.args.get("offset", 0)),
        )
    )


@tablero_bp.get("/orders/count")
def orders_count():
    f = _filters_from_request()
    return jsonify(
        {
            "total": queries.count_orders(
                country=request.args.get("country"),
                item_type=f.get("item_type"),
                channel=f.get("channel"),
                priority=f.get("priority"),
                region=f.get("region"),
                months=f.get("months"),
            )
        }
    )


@tablero_bp.post("/sales_records/generate")
@admin_required
def generate():
    body = request.get_json(silent=True) or {}
    count = int(body.get("count", 0) or 0)
    year_raw = body.get("year")
    year = int(year_raw) if year_raw not in (None, "") else None
    if count < 1:
        return jsonify({"status": "error", "message": "count inválido"}), 400
    try:
        result = generar_ventas.generate_sales(count, year=year)
        queries.clear_query_cache()
        return jsonify({"status": "ok", **result})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@tablero_bp.get("/elt_status")
def elt_status():
    from paquetes.datos import services as datos_services

    return jsonify(datos_services.get_elt_status())
