# -*- coding: utf-8 -*-
"""Generación PDF para informes simples y compuestos."""
from __future__ import annotations

import io
from datetime import datetime
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
    "indicador": "Indicador",
    "valor": "Valor",
    "estado": "Estado",
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
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    story: list[Any] = []

    story.append(Paragraph(_pdf_text("GLOBTRADE - Informe"), styles["Title"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(_pdf_text(f"{report_id} - {title}"), styles["Heading2"]))
    if subtitle:
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(_pdf_text(subtitle), styles["Normal"]))
    story.append(Spacer(1, 0.15 * cm))
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    row_count = total if total is not None else len(rows)
    story.append(Paragraph(_pdf_text(f"Generado: {generated}  |  Filas: {row_count}"), styles["Normal"]))
    story.append(Spacer(1, 0.35 * cm))

    headers = [_pdf_text(COLUMN_LABELS.get(c, c)) for c in columns]
    table_data = [headers]
    for row in rows:
        table_data.append([_cell(row.get(c)) for c in columns])

    if len(table_data) == 1:
        table_data.append(["Sin datos para este informe."] + [""] * (len(columns) - 1))

    font_size = 8 if len(columns) > 8 else 9
    col_width = (doc.width - 0.5 * cm) / max(len(columns), 1)
    table = Table(table_data, colWidths=[col_width] * len(columns), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            _pdf_text("Documento generado por GLOBTRADE (demo academica)."),
            styles["Italic"],
        )
    )
    doc.build(story)
    return buf.getvalue()
