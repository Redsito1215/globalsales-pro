# -*- coding: utf-8 -*-
"""API reportes simples y compuestos — Tarea 11 / Evaluación."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request, session

from auth.decorators import login_required, permission_required
from paquetes.reportes import ai_service, compuestos, services
from paquetes.reportes.pdf_export import generate_report_pdf
from paquetes.reportes.csv_export import generate_report_csv
from shared.mongo import get_db

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
        return jsonify({"status": "ok", "generated_at": datetime.now(timezone.utc).isoformat(), **data})
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
        return jsonify({"status": "ok", "generated_at": datetime.now(timezone.utc).isoformat(), **data})
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


def _record_export(report_id: str, export_format: str, row_count: int, report_type: str) -> None:
    get_db()["report_exports"].insert_one({
        "report_id": report_id.upper(), "format": export_format,
        "report_type": report_type, "row_count": int(row_count),
        "actor_email": session.get("email"), "actor_role": session.get("role"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def _csv_response(payload: bytes, filename: str) -> Response:
    return Response(
        payload, mimetype="text/csv; charset=utf-8",
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
@permission_required("analysis.export")
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
    _record_export(rid, "pdf", len(data.get("rows") or []), "simple")
    return _pdf_response(pdf, f"globtrade-{rid}.pdf")


@reportes_bp.get("/reportes/<report_id>/csv")
@login_required
@permission_required("reportes.view")
@permission_required("analysis.export")
def export_report_csv(report_id: str):
    q = (request.args.get("q") or request.args.get("search") or "").strip() or None
    limit = min(int(request.args.get("limit", 500)), 2000)
    threshold = int(request.args.get("threshold", 20))
    try:
        data = services.run_report(report_id, q=q, limit=limit, threshold=threshold)
    except ValueError as exc:
        if str(exc) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise
    report = data.get("report") or {}
    rid = (report.get("id") or report_id).upper()
    rows = data.get("rows") or []
    payload = generate_report_csv(columns=report.get("columns") or [], rows=rows)
    _record_export(rid, "csv", len(rows), "simple")
    return _csv_response(payload, f"globtrade-{rid}.csv")


@reportes_bp.get("/compuestos/<report_id>/pdf")
@login_required
@permission_required("reportes.view")
@permission_required("analysis.export")
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
    _record_export(rid, "pdf", len(data.get("rows") or []), "compuesto")
    return _pdf_response(pdf, f"globtrade-{rid}.pdf")


@reportes_bp.get("/compuestos/<report_id>/csv")
@login_required
@permission_required("reportes.view")
@permission_required("analysis.export")
def export_complex_csv(report_id: str):
    limit = min(int(request.args.get("limit", 500)), 2000)
    try:
        data = compuestos.run_complex_report(report_id, limit=limit)
    except ValueError as exc:
        if str(exc) == "unknown_report":
            return jsonify({"status": "error", "message": "Informe no encontrado."}), 404
        raise
    report = data.get("report") or {}
    rid = (report.get("id") or report_id).upper()
    rows = data.get("rows") or []
    payload = generate_report_csv(columns=report.get("columns") or [], rows=rows)
    _record_export(rid, "csv", len(rows), "compuesto")
    return _csv_response(payload, f"globtrade-{rid}.csv")


@reportes_bp.get("/reportes/exportaciones")
@login_required
@permission_required("audit.read")
def export_history():
    rows = list(get_db()["report_exports"].find({}, {"_id": 0}).sort("created_at", -1).limit(100))
    return jsonify({"status": "ok", "exports": rows, "count": len(rows)})


@reportes_bp.get("/reportes/compuestos/<report_id>/pdf")
@login_required
@permission_required("reportes.view")
def export_complex_pdf_legacy(report_id: str):
    return export_complex_pdf(report_id)


@reportes_bp.get("/reportes/ia/catalogo")
@login_required
@permission_required("reportes.view")
def ai_catalog():
    scope = (request.args.get("scope") or "all").strip()
    try:
        data = ai_service.list_ai_catalog(scope=scope)
        return jsonify({"status": "ok", **data})
    except Exception:
        return jsonify({"status": "error", "message": "No se pudo cargar el catálogo de informes."}), 500


@reportes_bp.post("/reportes/ia/recomendar")
@login_required
@permission_required("reportes.view")
def ai_recommend():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or request.args.get("prompt") or "").strip() or None
    limit = min(int(body.get("limit") or request.args.get("limit") or 5), 8)
    scope = (body.get("scope") or request.args.get("scope") or "all").strip()
    try:
        data = ai_service.recommend_reports(prompt=prompt, limit=limit, scope=scope)
        return jsonify({"status": "ok", **data})
    except Exception:
        return jsonify({"status": "error", "message": "No se pudieron obtener recomendaciones."}), 500


@reportes_bp.post("/reportes/ia/generar")
@login_required
@permission_required("reportes.view")
def ai_generate():
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or "").strip()
    limit = min(int(body.get("limit") or 100), 500)
    threshold = int(body.get("threshold") or 20)
    scope = (body.get("scope") or "all").strip()
    if not prompt:
        return jsonify({"status": "error", "message": "Describe el informe que necesitas.", "code": "prompt_required"}), 400
    try:
        data = ai_service.generate_report_from_prompt(
            prompt=prompt, limit=limit, threshold=threshold, scope=scope
        )
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        code = str(e)
        if code == "prompt_required":
            return jsonify({"status": "error", "message": "Describe el informe que necesitas.", "code": code}), 400
        if code == "unknown_report":
            return jsonify({"status": "error", "message": "No hay un informe del catálogo que encaje.", "code": code}), 404
        if code == "no_match":
            return jsonify({"status": "error", "message": "No se encontró un informe compatible.", "code": code}), 404
        raise
