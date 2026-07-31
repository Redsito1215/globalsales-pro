"""Rutas Flask — paquete Q2 Análisis."""
from __future__ import annotations

import csv
import io

from flask import Blueprint, Response, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.tablero import queries

analisis_bp = Blueprint("analisis", __name__, url_prefix="/api")


def _filters():
    months = request.args.get("months")
    return {
        "region": request.args.get("region") or None,
        "item_type": request.args.get("item_type") or None,
        "channel": request.args.get("channel") or None,
        "priority": request.args.get("priority") or None,
        "months": int(months) if months else None,
    }


@analisis_bp.get("/analysis/trend")
def analysis_trend():
    f = _filters()
    months = int(request.args.get("months", f.get("months") or 24))
    return jsonify(queries.monthly_trend(months, **f))


@analisis_bp.get("/analysis/regions")
def analysis_regions():
    f = _filters()
    return jsonify(
        {
            "regions": queries.revenue_by_region(**f),
            "countries": queries.top_countries(int(request.args.get("top", 20)), **f),
        }
    )


@analisis_bp.get("/analysis/products")
def analysis_products():
    return jsonify(queries.revenue_by_product(**_filters()))


@analisis_bp.get("/analysis/channels")
def analysis_channels():
    return jsonify(queries.channel_breakdown(**_filters()))


@analisis_bp.get("/analysis/export")
@login_required
@permission_required("analysis.export")
def analysis_export():
    f = _filters()
    limit = min(int(request.args.get("limit", 5000)), 50000)
    rows = queries.search_orders(
        country=request.args.get("country"),
        item_type=f.get("item_type"),
        channel=f.get("channel"),
        priority=f.get("priority"),
        region=f.get("region"),
        months=f.get("months"),
        limit=limit,
        offset=0,
    )
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    else:
        buf.write("sin_datos\n")
    truncated = len(rows) >= limit
    headers = {
        "Content-Disposition": "attachment; filename=globtrade_export.csv",
        "X-Export-Rows": str(len(rows)),
        "X-Export-Limit": str(limit),
        "X-Export-Truncated": "1" if truncated else "0",
    }
    return Response(buf.getvalue(), mimetype="text/csv", headers=headers)
