# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request, session

from auth.decorators import login_required, permission_required
from auth import roles_service
from paquetes.soporte import services
from paquetes.ventas import services as ventas

soporte_bp = Blueprint("soporte", __name__, url_prefix="/api/soporte")


def _is_staff() -> bool:
    role = session.get("role")
    return role == "administrador" or roles_service.has_permission(role, "soporte.inbox")


@soporte_bp.get("/hilos")
@login_required
@permission_required("soporte.inbox")
def listar_hilos():
    data = services.list_threads(limit=min(int(request.args.get("limit", 50)), 200))
    return jsonify({"status": "ok", **data})


@soporte_bp.get("/mensajes")
@login_required
def listar_mensajes():
    email = (session.get("email") or "").strip()
    thread = (request.args.get("thread") or email).strip().lower()
    if not _is_staff() and thread != email.lower():
        return jsonify({"status": "error", "message": "No puedes ver este hilo."}), 403
    if _is_staff() and not thread:
        return jsonify({"status": "error", "message": "Indica el hilo del cliente."}), 400
    after = int(request.args.get("after", 0) or 0)
    data = services.list_thread(thread, after_id=after)
    return jsonify({"status": "ok", **data})


@soporte_bp.post("/mensajes")
@login_required
def enviar_mensaje():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    thread = (body.get("thread_email") or session.get("email") or "").strip().lower()
    staff = _is_staff() and bool(body.get("as_staff"))
    if staff and not body.get("thread_email"):
        return jsonify({"status": "error", "message": "Indique el hilo del cliente."}), 400
    if not staff:
        thread = (session.get("email") or "").strip().lower()
    try:
        msg = services.post_message(
            author_email=session.get("email") or "",
            author_name=session.get("name") or "",
            text=text,
            thread_email=thread,
            staff=staff,
        )
        return jsonify({"status": "ok", "message": msg}), 201
    except ValueError as e:
        code = str(e)
        if code == "message_required":
            return jsonify({"status": "error", "message": "Escribe un mensaje."}), 400
        if code == "message_too_long":
            return jsonify({"status": "error", "message": "El mensaje no puede superar 100 palabras."}), 400
        raise


@soporte_bp.get("/solicitudes/<int:request_id>/factura.pdf")
@login_required
def factura_pdf(request_id: int):
    req = ventas.get_request(request_id)
    if not req:
        return jsonify({"status": "error", "message": "Solicitud no encontrada."}), 404
    email = (session.get("email") or "").strip().lower()
    role = session.get("role")
    if role not in ("administrador", "vendedor") and req.get("client_email", "").lower() != email:
        return jsonify({"status": "error", "message": "No autorizado."}), 403
    try:
        pdf = services.generate_invoice_pdf(req)
    except ImportError:
        return jsonify(
            {
                "status": "error",
                "message": "Generación PDF no disponible (falta reportlab en el servidor).",
                "code": "pdf_unavailable",
            }
        ), 503
    except Exception:
        return jsonify(
            {"status": "error", "message": "No se pudo generar el PDF.", "code": "pdf_error"}
        ), 500
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="altavia-trade-solicitud-{request_id}.pdf"'},
    )
