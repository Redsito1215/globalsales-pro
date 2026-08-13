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


def list_thread(user_email: str, *, limit: int = 100, after_id: int = 0) -> dict[str, Any]:
    email = (user_email or "").strip().lower()
    query: dict[str, Any] = {"$or": [{"thread_email": email}, {"recipient_email": email}]}
    after = max(int(after_id or 0), 0)
    if after > 0:
        query["message_id"] = {"$gt": after}
    rows = list(_col().find(query, {"_id": 0}).sort("message_id", 1).limit(limit))
    latest_id = after
    if rows:
        latest_id = max(int(r.get("message_id") or 0) for r in rows)
    elif after == 0:
        last = _col().find_one(query, {"message_id": 1}, sort=[("message_id", -1)])
        latest_id = int(last["message_id"]) if last else 0
    return {"thread_email": email, "messages": rows, "latest_id": latest_id}


def list_threads(*, limit: int = 50) -> dict[str, Any]:
    """Bandeja de hilos para staff: último mensaje por thread_email."""
    pipeline = [
        {"$sort": {"message_id": -1}},
        {
            "$group": {
                "_id": "$thread_email",
                "last_message": {"$first": "$text"},
                "last_at": {"$first": "$created_at"},
                "last_author": {"$first": "$author_name"},
                "staff_last": {"$first": "$staff"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"last_at": -1}},
        {"$limit": min(limit, 200)},
    ]
    rows = []
    for doc in _col().aggregate(pipeline):
        rows.append(
            {
                "thread_email": doc["_id"],
                "last_message": doc.get("last_message"),
                "last_at": doc.get("last_at"),
                "last_author": doc.get("last_author"),
                "awaiting_staff": not bool(doc.get("staff_last")),
                "message_count": doc.get("count") or 0,
            }
        )
    return {"total": len(rows), "threads": rows}


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
    words = [w for w in body.split() if w]
    if len(words) > 100:
        raise ValueError("message_too_long")
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

    from shared.notifications import notify_roles, notify_user

    if staff and thread and thread != author_email:
        notify_user(
            recipient_email=thread,
            subject="Respuesta de soporte GLOBTRADE",
            body=f"{doc['author_name']}: {body[:240]}",
            category="soporte",
            meta={"thread_email": thread},
        )
    elif not staff:
        notify_roles(
            roles=("vendedor", "administrador"),
            subject=f"Nuevo mensaje de soporte — {thread}",
            body=f"{doc['author_name']}: {body[:240]}",
            category="soporte",
            meta={"thread_email": thread},
            exclude_email=author_email,
        )
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


def _format_invoice_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
    except ValueError:
        return raw[:10]
    months = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    return f"{dt.day} de {months[dt.month - 1]} de {dt.year}"


def _invoice_number(request: dict[str, Any]) -> str:
    rid = request.get("request_id") or "-"
    raw = str(request.get("created_at") or "")
    year = datetime.now(timezone.utc).year
    if raw[:4].isdigit():
        year = int(raw[:4])
    return f"GBT-{year}-{int(rid):05d}" if str(rid).isdigit() else f"GBT-{year}-{rid}"


def _order_status_label(status: str | None) -> str:
    labels = {
        "pendiente": "Pendiente",
        "aprobada": "Aprobada",
        "convertida": "Convertida",
        "enviada": "Enviada",
        "entregada": "Entregada",
        "rechazada": "Rechazada",
        "cancelada": "Cancelada",
        "devuelta": "Devuelta",
    }
    key = (status or "").strip()
    return labels.get(key, key.replace("_", " ") if key else "—")


def _payment_status_label(status: str | None) -> str:
    labels = {
        "pendiente_pago": "Pendiente de pago",
        "pagado": "Pagado",
        "credito": "Credito comercial",
    }
    key = (status or "").strip()
    return labels.get(key, key.replace("_", " ") if key else "—")


def _payment_method_label(method: str | None) -> str:
    if not method:
        return ""
    labels = {
        "transferencia": "Transferencia bancaria",
        "tarjeta": "Tarjeta",
    }
    key = str(method).strip().lower()
    return labels.get(key, str(method).replace("_", " "))


def _billing_lines(request: dict[str, Any]) -> list[tuple[str, str]]:
    """Datos reales del cliente y destino de entrega."""
    lines: list[tuple[str, str]] = []
    name = (request.get("client_name") or "").strip()
    if name:
        lines.append(("Cliente", name))
    country = (request.get("country_name") or "").strip()
    if country:
        lines.append(("Pais destino", country))
    destination = (request.get("shipping_destination") or "").strip()
    if destination:
        lines.append(("Destino entrega", destination))
    region = (request.get("shipping_region") or "").strip()
    if region and region.lower() != (country or "").lower():
        lines.append(("Region envio", region))
    email = (request.get("client_email") or "").strip()
    if email:
        lines.append(("Correo", email))
    phone = (request.get("client_phone") or "").strip()
    if phone:
        lines.append(("Telefono", phone))
    return lines


def _sale_summary_lines(request: dict[str, Any]) -> list[tuple[str, str]]:
    """Solo datos reales del pedido; sin cuentas bancarias inventadas."""
    from paquetes.ventas.services import display_order_id

    lines: list[tuple[str, str]] = [
        ("Solicitud", f"#{request.get('request_id', '—')}"),
    ]
    if request.get("order_id"):
        lines.append(
            (
                "Pedido venta",
                display_order_id(request.get("order_id"), request.get("request_id")),
            )
        )
    if request.get("channel_name") or request.get("channel_id"):
        lines.append(("Canal", str(request.get("channel_name") or request.get("channel_id"))))
    lines.append(("Estado pedido", _order_status_label(request.get("status"))))
    lines.append(("Estado pago", _payment_status_label(request.get("payment_status"))))
    method = _payment_method_label(request.get("payment_method"))
    if method:
        lines.append(("Metodo de pago", method))
    shipping = float(request.get("shipping_cost") or 0)
    if shipping > 0:
        lines.append(("Costo envio", f"${shipping:,.2f}"))
    if request.get("paid_at"):
        lines.append(("Pagado el", str(request.get("paid_at"))))
    if request.get("tracking_number"):
        lines.append(("Seguimiento", str(request.get("tracking_number"))))
    if request.get("shipped_at"):
        lines.append(("Enviado", str(request.get("shipped_at"))))
    if request.get("delivered_at"):
        lines.append(("Entregado", str(request.get("delivered_at"))))
    return lines


def _fit_text(c, text: str, font: str, size: float, max_width: float) -> str:
    t = _pdf_text(text)
    c.setFont(font, size)
    if c.stringWidth(t, font, size) <= max_width:
        return t
    while t and c.stringWidth(t + "...", font, size) > max_width:
        t = t[:-1]
    return (t + "...") if t else "..."


def _label_column_width(
    c,
    rows: list[tuple[str, str]],
    *,
    font: str = "Helvetica-Bold",
    size: float = 8.5,
    padding: float = 0.28,
    min_w: float = 2.0,
    max_w: float = 3.55,
) -> float:
    from reportlab.lib.units import cm

    c.setFont(font, size)
    width = min_w * cm
    pad = padding * cm
    cap = max_w * cm
    for label, _ in rows:
        width = max(width, c.stringWidth(f"{label}:", font, size) + pad)
    return min(width, cap)


def _draw_company_brand(c, x: float, y: float, profile: dict[str, Any]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader

    from shared.company_profile import static_path_from_url

    name = _pdf_text(profile.get("legal_name") or profile.get("name") or "GLOBTRADE")
    tagline = _pdf_text(profile.get("tagline") or "")
    text_x = x
    logo_path = static_path_from_url(profile.get("logo_url"))
    if logo_path and logo_path.is_file():
        try:
            ir = ImageReader(str(logo_path))
            iw, ih = ir.getSize()
            max_side = 1.15 * cm
            scale = min(max_side / max(iw, 1), max_side / max(ih, 1))
            lw, lh = iw * scale, ih * scale
            c.drawImage(ir, x, y - lh * 0.15, width=lw, height=lh, mask="auto")
            text_x = x + lw + 0.28 * cm
        except Exception:
            _draw_logo_mark(c, x, y)
            return

    c.setFillColor(colors.HexColor("#1a1f4b"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(text_x, y, name)
    if tagline:
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawString(text_x, y - 11, _fit_text(c, tagline, "Helvetica", 7.5, 5.2 * cm))


def _draw_logo_mark(c, x: float, y: float) -> None:
    from reportlab.lib import colors

    c.setFillColor(colors.HexColor("#7c3aed"))
    c.circle(x, y + 6, 4, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#14b8a6"))
    c.circle(x + 7, y + 2, 3.5, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1a1f4b"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 16, y, "GLOBTRADE")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(x + 16, y - 11, "S.A.")


def generate_invoice_pdf(request: dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    from shared.company_profile import get_company_profile

    profile = get_company_profile()
    NAVY = colors.HexColor("#1a1f4b")
    LIGHT = colors.HexColor("#f2f2f2")
    ROW_ALT = colors.HexColor("#f7f7f7")
    MUTED = colors.HexColor("#64748b")
    BORDER = colors.HexColor("#e2e8f0")

    margin_x = 1.35 * cm
    margin_top = 1.2 * cm
    content_w = A4[0] - 2 * margin_x

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    def new_page() -> float:
        c.showPage()
        return h - margin_top

    y = h - margin_top

    # ── Header band ─────────────────────────────────────────────────────
    band_h = 1.55 * cm
    c.setFillColor(NAVY)
    c.rect(margin_x, y - band_h, 5.8 * cm, band_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin_x + 0.45 * cm, y - 1.05 * cm, "FACTURA")
    _draw_company_brand(c, w - margin_x - 5.2 * cm, y - 1.05 * cm, profile)
    y -= band_h + 0.55 * cm

    inv_no = _invoice_number(request)
    inv_date = _format_invoice_date(request.get("created_at"))

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_x, y, "No. de factura")
    c.drawRightString(w - margin_x, y, "Fecha")
    y -= 0.38 * cm
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, _pdf_text(inv_no))
    c.drawRightString(w - margin_x, y, _pdf_text(inv_date))
    y -= 0.75 * cm

    # ── Billing / payment blocks ───────────────────────────────────────
    col_gap = 0.45 * cm
    col_w = (content_w - col_gap) / 2
    left_x = margin_x
    right_x = margin_x + col_w + col_gap
    billing_lines = _billing_lines(request) or [("Cliente", request.get("client_name") or "Cliente")]
    summary_lines = _sale_summary_lines(request)
    row_step = 0.46 * cm
    left_label_w = _label_column_width(c, billing_lines)
    right_label_w = _label_column_width(c, summary_lines)
    block_h = max(3.35 * cm, 1.2 * cm + max(len(billing_lines), len(summary_lines)) * row_step)

    c.setStrokeColor(BORDER)
    c.setFillColor(colors.white)
    c.rect(left_x, y - block_h, col_w, block_h, fill=1, stroke=1)
    c.rect(right_x, y - block_h, col_w, block_h, fill=1, stroke=1)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_x + 0.35 * cm, y - 0.55 * cm, "Facturar a")
    c.drawString(right_x + 0.35 * cm, y - 0.55 * cm, "Resumen del pedido")

    def draw_labeled_lines(
        x: float,
        start_y: float,
        rows: list[tuple[str, str]],
        label_w: float,
    ) -> None:
        row_y = start_y
        value_x = x + 0.35 * cm + label_w
        value_w = col_w - label_w - 0.7 * cm
        for label, value in rows:
            c.setFillColor(MUTED)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(x + 0.35 * cm, row_y, f"{label}:")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8.5)
            c.drawString(value_x, row_y, _fit_text(c, value, "Helvetica", 8.5, value_w))
            row_y -= row_step

    draw_labeled_lines(left_x, y - 1.05 * cm, billing_lines, left_label_w)
    draw_labeled_lines(right_x, y - 1.05 * cm, summary_lines, right_label_w)

    y -= block_h + 0.65 * cm

    # ── Line items table ────────────────────────────────────────────────
    cols = [
        ("Artículo", 1.0 * cm, "center"),
        ("Descripción", 7.4 * cm, "left"),
        ("Cant.", 1.5 * cm, "center"),
        ("Precio", 2.35 * cm, "right"),
        ("Total", 2.35 * cm, "right"),
    ]
    row_h = 0.72 * cm
    header_h = 0.78 * cm

    def table_x(col_idx: int) -> float:
        x = margin_x
        for i in range(col_idx):
            x += cols[i][1]
        return x

    def draw_table_header(at_y: float) -> float:
        c.setFillColor(NAVY)
        c.rect(margin_x, at_y - header_h, content_w, header_h, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        for idx, (label, width, align) in enumerate(cols):
            tx = table_x(idx)
            if align == "center":
                c.drawCentredString(tx + width / 2, at_y - 0.52 * cm, label)
            elif align == "right":
                c.drawRightString(tx + width - 0.12 * cm, at_y - 0.52 * cm, label)
            else:
                c.drawString(tx + 0.12 * cm, at_y - 0.52 * cm, label)
        return at_y - header_h

    y = draw_table_header(y)
    subtotal = 0.0
    line_items = request.get("lines") or []

    for i, line in enumerate(line_items, start=1):
        if y < 5.5 * cm:
            y = new_page()
            y = draw_table_header(y)

        qty = int(line.get("quantity") or 0)
        price = float(line.get("unit_price") or 0)
        gross = float(line.get("line_gross") if line.get("line_gross") is not None else qty * price)
        disc = float(line.get("discount_alloc") or 0)
        net = float(line.get("line_net") if line.get("line_net") is not None else max(gross - disc, 0))
        subtotal += gross

        fill = ROW_ALT if i % 2 == 0 else colors.white
        c.setFillColor(fill)
        c.rect(margin_x, y - row_h, content_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(BORDER)
        c.line(margin_x, y - row_h, margin_x + content_w, y - row_h)

        name = line.get("product_name") or f"Producto {line.get('product_id', '')}"
        sku = line.get("product_id")
        desc = name if not sku else f"{name} (SKU {sku})"

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawCentredString(table_x(0) + cols[0][1] / 2, y - 0.48 * cm, str(i))
        c.drawString(table_x(1) + 0.12 * cm, y - 0.48 * cm, _fit_text(c, desc, "Helvetica", 9, cols[1][1] - 0.24 * cm))
        c.drawCentredString(table_x(2) + cols[2][1] / 2, y - 0.48 * cm, str(qty))
        c.drawRightString(table_x(3) + cols[3][1] - 0.12 * cm, y - 0.48 * cm, f"${price:,.2f}")
        c.drawRightString(table_x(4) + cols[4][1] - 0.12 * cm, y - 0.48 * cm, f"${gross:,.2f}")
        y -= row_h

    discount = float(request.get("discount_amount") or 0)
    shipping = float(request.get("shipping_cost") or 0)
    total = float(
        request.get("total")
        if request.get("total") is not None
        else max(subtotal - discount + shipping, 0)
    )

    if y < 6.2 * cm:
        y = new_page()

    # ── Totals ──────────────────────────────────────────────────────────
    totals_w = 6.4 * cm
    totals_x = w - margin_x - totals_w
    extra_rows = (1 if discount > 0 else 0) + (1 if shipping > 0 else 0)
    totals_h = 1.85 * cm + extra_rows * 0.55 * cm
    y -= 0.35 * cm

    c.setFillColor(colors.white)
    c.setStrokeColor(BORDER)
    c.rect(totals_x, y - totals_h, totals_w, totals_h, fill=1, stroke=1)

    ty = y - 0.55 * cm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(totals_x + 0.35 * cm, ty, "Subtotal")
    c.drawRightString(w - margin_x - 0.35 * cm, ty, f"${subtotal:,.2f}")
    ty -= 0.55 * cm
    if shipping > 0:
        c.drawString(totals_x + 0.35 * cm, ty, "Envio")
        c.drawRightString(w - margin_x - 0.35 * cm, ty, f"${shipping:,.2f}")
        ty -= 0.55 * cm
    if discount > 0:
        code = request.get("discount_code") or "Descuento"
        c.drawString(totals_x + 0.35 * cm, ty, _fit_text(c, f"Descuento ({code})", "Helvetica", 9, totals_w - 2.5 * cm))
        c.drawRightString(w - margin_x - 0.35 * cm, ty, f"-${discount:,.2f}")
        ty -= 0.55 * cm

    c.setFillColor(LIGHT)
    c.rect(totals_x + 0.2 * cm, ty - 0.72 * cm, totals_w - 0.4 * cm, 0.72 * cm, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(totals_x + 0.35 * cm, ty - 0.52 * cm, "Total")
    c.drawRightString(w - margin_x - 0.35 * cm, ty - 0.52 * cm, f"${total:,.2f}")

    y -= totals_h + 0.9 * cm

    # ── Footer ──────────────────────────────────────────────────────────
    if y < 3.8 * cm:
        y = new_page()

    footer_y = 2.35 * cm
    c.setStrokeColor(BORDER)
    c.line(margin_x, footer_y + 1.35 * cm, w - margin_x, footer_y + 1.35 * cm)

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(margin_x, footer_y + 0.95 * cm, _pdf_text(inv_date))
    c.setStrokeColor(colors.black)
    c.line(margin_x, footer_y + 0.55 * cm, margin_x + 5.5 * cm, footer_y + 0.55 * cm)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_x, footer_y + 0.15 * cm, _pdf_text(profile.get("invoice_signer") or "Equipo Comercial GLOBTRADE"))

    info_x = w - margin_x - 6.8 * cm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(NAVY)
    c.drawString(info_x, footer_y + 1.05 * cm, "Referencia")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.black)
    info_lines = [inv_no, f"Solicitud #{request.get('request_id', '—')}"]
    if request.get("order_id"):
        info_lines.append(f"Pedido venta {request.get('order_id')}")
    info_lines.append(_pdf_text(profile.get("legal_name") or "GLOBTRADE S.A.") + " — plataforma comercial")
    iy = footer_y + 0.62 * cm
    for line in info_lines:
        c.drawString(info_x, iy, line)
        iy -= 0.38 * cm

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(MUTED)
    c.drawCentredString(
        w / 2,
        1.15 * cm,
        _pdf_text(profile.get("invoice_footer") or "Documento comercial GLOBTRADE (demo academica). No es factura fiscal."),
    )

    c.showPage()
    c.save()
    return buf.getvalue()
