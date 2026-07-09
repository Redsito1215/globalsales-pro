# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request, session

from auth.decorators import admin_required, login_required
from paquetes.soporte import services
from paquetes.ventas import services as ventas

soporte_bp = Blueprint("soporte", __name__, url_prefix="/api/soporte")


@soporte_bp.get("/mensajes")
@login_required
def listar_mensajes():
    email = (session.get("email") or "").strip()
    thread = (request.args.get("thread") or email).strip().lower()
    role = session.get("role")
    if role != "administrador" and thread != email.lower():
        return jsonify({"status": "error", "message": "No puedes ver este hilo."}), 403
    data = services.list_thread(thread)
    return jsonify({"status": "ok", **data})


@soporte_bp.post("/mensajes")
@login_required
def enviar_mensaje():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    thread = (body.get("thread_email") or session.get("email") or "").strip().lower()
    role = session.get("role")
    staff = role in ("administrador", "vendedor") and body.get("as_staff")
    if staff and role != "administrador" and not body.get("thread_email"):
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
        headers={"Content-Disposition": f'inline; filename="globtrade-solicitud-{request_id}.pdf"'},
    )
