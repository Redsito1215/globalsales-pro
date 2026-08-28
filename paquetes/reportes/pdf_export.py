# -*- coding: utf-8 -*-
"""Generación PDF para informes simples y compuestos."""
from __future__ import annotations

import io
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape
from typing import Any

COLUMN_LABELS: dict[str, str] = {
    "request_id": "N. solicitud",
    "client_name": "Cliente",
    "client_email": "Correo",
    "status": "Estado",
    "payment_status": "Pago",
    "total": "Total",
    "created_at": "Fecha",
    "sku": "Codigo",
    "product_name": "Producto",
    "inventory_quantity": "Stock",
    "unit_price": "Precio",
    "unit_cost": "Costo",
    "vendor_name": "Proveedor",
    "thread_email": "Cliente",
    "last_body": "Ultimo mensaje",
    "last_at": "Fecha",
    "message_count": "Mensajes",
    "espera_respuesta": "Espera respuesta",
    "po_id": "Orden",
    "notes": "Notas",
    "received_at": "Recibida",
    "vendor_id": "Codigo",
    "name": "Nombre",
    "country": "Pais",
    "email": "Correo",
    "phone": "Telefono",
    "active": "Activo",
    "order_id": "N. venta",
    "tracking": "Seguimiento",
    "shipped_at": "Enviado",
    "code": "Cupon",
    "discount_type": "Tipo",
    "value": "Valor",
    "uses": "Usos",
    "max_uses": "Limite",
    "role": "Rol",
    "category": "Categoria",
    "reviewed_by": "Reviso",
    "mes": "Mes",
    "categoria": "Categoria",
    "pedidos": "Pedidos",
    "unidades": "Unidades",
    "ingresos": "Ingresos",
    "utilidad": "Utilidad",
    "ranking": "#",
    "grupo": "Grupo",
    "concepto": "Concepto",
    "monto": "Monto",
    "detalle": "Detalle",
    "unidades_vendidas": "Unidades vendidas",
    "stock_actual": "Stock actual",
    "rotacion_aprox": "Rotacion aprox.",
    "region": "Region",
    "dias_promedio": "Dias promedio",
    "cupon": "Cupon",
    "usos_landing": "Usos",
    "ingresos_con_cupon": "Ingresos c/cupon",
    "descuento_total": "Descuento",
    "activo": "Activo",
    "costos": "Costos",
    "margen_pct": "Margen %",
    "proveedor": "Proveedor",
    "ordenes": "Ordenes",
    "participacion_pct": "Participacion %",
    "ticket_promedio": "Ticket promedio",
    "riesgo": "Riesgo",
    "decision": "Decision",
    "indicador": "Indicador",
    "valor": "Valor",
    "estado": "Estado",
    "item_type": "Categoria",
    "sales_channel": "Canal",
    "order_priority": "Prioridad",
    "order_date": "Fecha",
    "units_sold": "Unidades",
    "total_revenue": "Ingresos",
    "total_profit": "Utilidad",
    "fecha": "Fecha",
    "modulo": "Modulo",
    "accion": "Accion",
    "entidad": "Entidad",
    "referencia": "Referencia",
    "usuario": "Usuario",
    "rol": "Rol",
    "cambios": "Cambios",
}


def _pdf_text(value: Any) -> str:
    text = str(value if value is not None else "-")
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u00b7", " - ")
        .replace("\u2022", "-")
        .replace("\u00ba", "o")
        .replace("\u00a0", " ")
    )


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "Si" if value else "No"
    return _pdf_text(value)


def generate_report_pdf(
    *,
    report_id: str,
    title: str,
    subtitle: str | None,
    columns: list[str],
    rows: list[dict[str, Any]],
    total: int | None = None,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from shared.company_profile import get_company_profile, static_path_from_url

    page_size = landscape(A4) if len(columns) > 6 else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    profile = get_company_profile()
    company_name = profile.get("name") or profile.get("legal_name") or "Altavia Trade"
    cell_style = ParagraphStyle("Cell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9, spaceAfter=0)
    head_style = ParagraphStyle("Head", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white, fontSize=7.4, leading=9)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#52606d"))
    right_style = ParagraphStyle("Right", parent=meta_style, alignment=TA_RIGHT)
    story: list[Any] = []
    logo_path = static_path_from_url(profile.get("logo_url"))
    brand_left: Any = Paragraph(f"<b>{escape(_pdf_text(company_name))}</b><br/><font size='8'>{escape(_pdf_text(profile.get('tagline') or ''))}</font>", styles["Heading2"])
    if logo_path and logo_path.exists():
        try:
            brand_left = Table([[Image(str(logo_path), width=1.35*cm, height=1.35*cm), brand_left]], colWidths=[1.55*cm, doc.width*0.55])
        except Exception:
            pass
    brand = Table([[brand_left, Paragraph("INFORME GERENCIAL", right_style)]], colWidths=[doc.width*0.72, doc.width*0.28])
    brand.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,-1),1,colors.HexColor("#176b5d")),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.append(brand)
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(escape(_pdf_text(title)), styles["Title"]))
    story.append(Paragraph(escape(_pdf_text(f"Código: {report_id}")), meta_style))
    if subtitle:
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(escape(_pdf_text(subtitle)), styles["Normal"]))
    story.append(Spacer(1, 0.15 * cm))
    generated = datetime.now(ZoneInfo("America/Guayaquil")).strftime("%d/%m/%Y %H:%M")
    row_count = total if total is not None else len(rows)
    story.append(Paragraph(_pdf_text(f"Generado en hora de Ecuador: {generated}  |  Registros: {row_count}"), meta_style))
    story.append(Spacer(1, 0.35 * cm))

    headers = [Paragraph(escape(_pdf_text(COLUMN_LABELS.get(c, c))), head_style) for c in columns]
    table_data = [headers]
    for row in rows:
        table_data.append([Paragraph(escape(_cell(row.get(c))), cell_style) for c in columns])

    if len(table_data) == 1:
        table_data.append(["Sin datos para este informe."] + [""] * (len(columns) - 1))

    font_size = 7 if len(columns) > 10 else 8 if len(columns) > 8 else 9
    col_width = (doc.width - 0.5 * cm) / max(len(columns), 1)
    table = LongTable(table_data, colWidths=[col_width] * len(columns), repeatRows=1, splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176b5d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ccd5d2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8f6")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            _pdf_text(f"Documento generado por {company_name}. Los valores reflejan los filtros aplicados."),
            styles["Italic"],
        )
    )
    doc.build(story)
    return buf.getvalue()
