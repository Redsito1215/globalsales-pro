# -*- coding: utf-8 -*-
"""Soporte — chat y facturación PDF."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from shared.mongo import get_db

COLLECTION = "support_messages"


def _col():
    return get_db()[COLLECTION]


def _next_id() -> int:
    row = _col().find_one({}, {"message_id": 1}, sort=[("message_id", -1)])
    return int(row["message_id"]) + 1 if row and row.get("message_id") else 1


def list_thread(user_email: str, *, limit: int = 100) -> dict[str, Any]:
    email = (user_email or "").strip().lower()
    query = {"$or": [{"thread_email": email}, {"recipient_email": email}]}
    rows = list(_col().find(query, {"_id": 0}).sort("message_id", 1).limit(limit))
    return {"thread_email": email, "messages": rows}


def post_message(
    *,
    author_email: str,
    author_name: str,
    text: str,
    thread_email: str | None = None,
    staff: bool = False,
) -> dict[str, Any]:
    body = (text or "").strip()
    if not body:
        raise ValueError("message_required")
    author_email = (author_email or "").strip().lower()
    thread = (thread_email or author_email).strip().lower()
    doc = {
        "message_id": _next_id(),
        "thread_email": thread,
        "author_email": author_email,
        "author_name": (author_name or author_email).strip(),
        "text": body[:2000],
        "staff": bool(staff),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _col().insert_one(doc)
    doc.pop("_id", None)
    return doc


def _pdf_text(value: Any) -> str:
    """Helvetica solo admite Latin-1; normalizamos caracteres habituales."""
    text = str(value if value is not None else "-")
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u00b7", " - ")
        .replace("\u2022", "-")
        .replace("\u00ba", "o")
        .replace("\u00a0", " ")
    )


def generate_invoice_pdf(request: dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, _pdf_text("GLOBTRADE S.A. - Comprobante de solicitud"))
    y -= 1 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, _pdf_text(f"Solicitud No. {request.get('request_id', '-')}"))
    y -= 0.5 * cm
    c.drawString(
        2 * cm,
        y,
        _pdf_text(
            f"Fecha: {request.get('created_at', '-')}  -  Estado: {request.get('status', '-')}"
        ),
    )
    y -= 0.8 * cm
    c.drawString(
        2 * cm,
        y,
        _pdf_text(f"Cliente: {request.get('client_name', '')} ({request.get('client_email', '')})"),
    )
    y -= 0.5 * cm
    if request.get("client_phone"):
        c.drawString(2 * cm, y, _pdf_text(f"Telefono: {request['client_phone']}"))
        y -= 0.5 * cm
    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Detalle de productos")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    subtotal = 0.0
    for line in request.get("lines") or []:
        qty = int(line.get("quantity") or 0)
        price = float(line.get("unit_price") or 0)
        total = qty * price
        subtotal += total
        name = line.get("product_name") or f"Producto {line.get('product_id')}"
        c.drawString(2 * cm, y, _pdf_text(f"- {name}  x{qty}  @ ${price:.2f}  = ${total:.2f}"))
        y -= 0.45 * cm
        if y < 3 * cm:
            c.showPage()
            y = h - 2 * cm
    discount = float(request.get("discount_amount") or 0)
    y -= 0.4 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, f"Subtotal: ${subtotal:.2f}")
    y -= 0.45 * cm
    if discount > 0:
        c.drawString(2 * cm, y, f"Descuento ({request.get('discount_code', '')}): -${discount:.2f}")
        y -= 0.45 * cm
    c.drawString(2 * cm, y, f"Total estimado: ${max(subtotal - discount, 0):.2f}")
    y -= 1 * cm
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, y, "Documento informativo generado por la plataforma GLOBTRADE (demo académica).")
    c.showPage()
    c.save()
    return buf.getvalue()
