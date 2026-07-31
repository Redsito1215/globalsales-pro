# -*- coding: utf-8 -*-
"""API reportes simples y compuestos — Tarea 11 / Evaluación."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.reportes import compuestos, services

reportes_bp = Blueprint("reportes", __name__, url_prefix="/api")


@reportes_bp.get("/reportes")
@login_required
@permission_required("reportes.view")
def catalog():
    return jsonify({"status": "ok", "reports": services.list_catalog(), "tipo": "simple"})


@reportes_bp.get("/reportes/compuestos")
@login_required
@permission_required("reportes.view")
def catalog_complex():
    return jsonify(
        {"status": "ok", "reports": compuestos.list_complex_catalog(), "tipo": "compuesto"}
    )


@reportes_bp.get("/reportes/compuestos/<report_id>")
@login_required
@permission_required("reportes.view")
def run_complex(report_id: str):
    limit = min(int(request.args.get("limit", 100)), 500)
    try:
        data = compuestos.run_complex_report(report_id, limit=limit)
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe compuesto no encontrado."}), 404
        raise


@reportes_bp.get("/reportes/<report_id>")
@login_required
@permission_required("reportes.view")
def run(report_id: str):
    if report_id.lower() == "compuestos":
        return catalog_complex()
    q = (request.args.get("q") or request.args.get("search") or "").strip() or None
    limit = min(int(request.args.get("limit", 100)), 500)
    threshold = int(request.args.get("threshold", 20))
    try:
        data = services.run_report(report_id, q=q, limit=limit, threshold=threshold)
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Reporte no encontrado."}), 404
        raise
