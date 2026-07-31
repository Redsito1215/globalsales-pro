"""Rutas — panel de decisiones de negocio."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.decisiones import services

decisiones_bp = Blueprint("decisiones", __name__, url_prefix="/api/decisiones")


@decisiones_bp.get("/panel")
@login_required
@permission_required("decisiones.view")
def panel():
    days = int(request.args.get("days", 7) or 7)
    threshold = int(request.args.get("stock_threshold", 20) or 20)
    limit = int(request.args.get("limit", 8) or 8)
    data = services.decision_panel(days=days, stock_threshold=threshold, limit=limit)
    return jsonify({"status": "ok", **data})


@decisiones_bp.get("/margen")
@login_required
@permission_required("decisiones.view")
def margen():
    limit = int(request.args.get("limit", 8) or 8)
    return jsonify({"status": "ok", **services.product_margin_ranking(limit=limit)})


@decisiones_bp.get("/stock")
@login_required
@permission_required("decisiones.view")
def stock():
    threshold = int(request.args.get("threshold", 20) or 20)
    return jsonify({"status": "ok", **services.low_stock(threshold=threshold)})


@decisiones_bp.get("/funnel")
@login_required
@permission_required("decisiones.view")
def funnel():
    days = int(request.args.get("days", 7) or 7)
    return jsonify({"status": "ok", **services.commercial_funnel(days=days)})
