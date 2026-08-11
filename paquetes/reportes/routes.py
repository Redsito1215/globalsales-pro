# -*- coding: utf-8 -*-
"""API reportes simples y compuestos — Tarea 11 / Evaluación."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.reportes import compuestos, services
from paquetes.reportes.pdf_export import generate_report_pdf

reportes_bp = Blueprint("reportes", __name__, url_prefix="/api")


@reportes_bp.get("/reportes")
@login_required
@permission_required("reportes.view")
def catalog():
    return jsonify({"status": "ok", "reports": services.list_catalog(), "tipo": "simple"})


@reportes_bp.get("/reportes/<report_id>")
@login_required
@permission_required("reportes.view")
def run(report_id: str):
    # No usar "compuestos" como id de reporte simple: va por /api/compuestos
    q = (request.args.get("q") or request.args.get("search") or "").strip() or None
    limit = min(int(request.args.get("limit", 100)), 500)
    threshold = int(request.args.get("threshold", 20))
    try:
        data = services.run_report(report_id, q=q, limit=limit, threshold=threshold)
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise


# Rutas propias (no comparten /reportes/<id>) para no chocar con los simples
@reportes_bp.get("/compuestos")
@login_required
@permission_required("reportes.view")
def catalog_complex():
    return jsonify(
        {"status": "ok", "reports": compuestos.list_complex_catalog(), "tipo": "compuesto"}
    )


@reportes_bp.get("/compuestos/<report_id>")
@login_required
@permission_required("reportes.view")
def run_complex(report_id: str):
    limit = min(int(request.args.get("limit", 100)), 500)
    try:
        data = compuestos.run_complex_report(report_id, limit=limit)
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise


# Compatibilidad con clientes antiguos
@reportes_bp.get("/reportes/compuestos")
@login_required
@permission_required("reportes.view")
def catalog_complex_legacy():
    return catalog_complex()


@reportes_bp.get("/reportes/compuestos/<report_id>")
@login_required
@permission_required("reportes.view")
def run_complex_legacy(report_id: str):
    return run_complex(report_id)


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_error_response(exc: Exception) -> tuple[Response, int]:
    if isinstance(exc, ImportError):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Generacion PDF no disponible (falta reportlab en el servidor).",
                    "code": "pdf_unavailable",
                }
            ),
            503,
        )
    return (
        jsonify({"status": "error", "message": "No se pudo generar el PDF.", "code": "pdf_error"}),
        500,
    )


@reportes_bp.get("/reportes/<report_id>/pdf")
@login_required
@permission_required("reportes.view")
def export_report_pdf(report_id: str):
    q = (request.args.get("q") or request.args.get("search") or "").strip() or None
    limit = min(int(request.args.get("limit", 200)), 500)
    threshold = int(request.args.get("threshold", 20))
    try:
        data = services.run_report(report_id, q=q, limit=limit, threshold=threshold)
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise
    report = data.get("report") or {}
    try:
        pdf = generate_report_pdf(
            report_id=report.get("id") or report_id.upper(),
            title=report.get("name") or "Informe",
            subtitle=report.get("para_que"),
            columns=report.get("columns") or [],
            rows=data.get("rows") or [],
            total=data.get("total"),
        )
    except Exception as exc:
        body, code = _pdf_error_response(exc)
        return body, code
    rid = (report.get("id") or report_id).upper()
    return _pdf_response(pdf, f"globtrade-{rid}.pdf")


@reportes_bp.get("/compuestos/<report_id>/pdf")
@login_required
@permission_required("reportes.view")
def export_complex_pdf(report_id: str):
    limit = min(int(request.args.get("limit", 200)), 500)
    try:
        data = compuestos.run_complex_report(report_id, limit=limit)
    except ValueError as e:
        if str(e) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise
    report = data.get("report") or {}
    try:
        pdf = generate_report_pdf(
            report_id=report.get("id") or report_id.upper(),
            title=report.get("name") or "Informe compuesto",
            subtitle=report.get("para_que"),
            columns=report.get("columns") or [],
            rows=data.get("rows") or [],
            total=data.get("total"),
        )
    except Exception as exc:
        body, code = _pdf_error_response(exc)
        return body, code
    rid = (report.get("id") or report_id).upper()
    return _pdf_response(pdf, f"globtrade-{rid}.pdf")


@reportes_bp.get("/reportes/compuestos/<report_id>/pdf")
@login_required
@permission_required("reportes.view")
def export_complex_pdf_legacy(report_id: str):
    return export_complex_pdf(report_id)
