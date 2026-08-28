"""Rutas Flask — paquete Q2 Análisis."""
from __future__ import annotations

import csv
import io

from flask import Blueprint, Response, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.tablero import queries
from paquetes.reportes.pdf_export import generate_report_pdf

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


@analisis_bp.get("/analysis/export/pdf")
@login_required
@permission_required("analysis.export")
def analysis_export_pdf():
    """Exporta las ventas filtradas en un documento PDF gerencial."""
    f = _filters()
    limit = min(max(int(request.args.get("limit", 5000)), 1), 5000)
    rows = queries.search_orders(
        country=request.args.get("country"), item_type=f.get("item_type"),
        channel=f.get("channel"), priority=f.get("priority"),
        region=f.get("region"), months=f.get("months"), limit=limit, offset=0,
    )
    columns = [
        "order_id", "country", "region", "item_type", "sales_channel",
        "order_priority", "order_date", "units_sold", "total_revenue", "total_profit",
    ]
    pdf = generate_report_pdf(
        report_id="VENTAS",
        title="Ventas filtradas",
        subtitle="Detalle comercial generado con los filtros seleccionados.",
        columns=columns,
        rows=rows,
        total=len(rows),
    )
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="altavia-trade-ventas.pdf"'},
    )


@analisis_bp.get("/analysis/preview")
@login_required
@permission_required("analysis.export")
def analysis_preview():
    """Vista previa liviana con los mismos filtros usados por el PDF."""
    f = _filters()
    requested_limit = min(max(int(request.args.get("limit", 5000)), 1), 50000)
    rows = queries.search_orders(
        country=request.args.get("country"),
        item_type=f.get("item_type"),
        channel=f.get("channel"),
        priority=f.get("priority"),
        region=f.get("region"),
        months=f.get("months"),
        limit=min(requested_limit, 25),
        offset=0,
    )
    total = queries.count_orders(
        country=request.args.get("country"), item_type=f.get("item_type"),
        channel=f.get("channel"), priority=f.get("priority"),
        region=f.get("region"), months=f.get("months"),
    )
    return jsonify({
        "status": "ok", "rows": rows, "preview_count": len(rows),
        "total": total, "export_count": min(total, requested_limit),
        "truncated": total > requested_limit,
    })
