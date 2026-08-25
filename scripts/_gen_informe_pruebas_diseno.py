# -*- coding: utf-8 -*-
"""Word académico: plan, ejecución, defectos resueltos, defectos abiertos y diseño."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement

OUT = Path(__file__).resolve().parents[1] / "docs" / "Informe-plan-pruebas-ejecucion-diseno.docx"

PURPLE = RGBColor(0x71, 0x4B, 0x67)
DARK = RGBColor(0x1F, 0x1A, 0x24)
MUTED = RGBColor(0x5A, 0x54, 0x62)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0x8B, 0x1E, 0x1E)


def set_run(run, *, size=11, bold=False, italic=False, color=DARK, font="Calibri"):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def add_para(doc, text, *, size=11, bold=False, italic=False, color=DARK, space_after=8, space_before=0, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = 1.15
    if align:
        p.alignment = align
    run = p.add_run(text)
    set_run(run, size=size, bold=bold, italic=italic, color=color)
    return p


def shade_heading(paragraph, fill="714B67"):
    pPr = paragraph._p.get_or_add_pPr()
    shd = pPr.makeelement(
        qn("w:shd"),
        {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): fill},
    )
    pPr.append(shd)
    paragraph.paragraph_format.left_indent = Cm(-0.5)
    paragraph.paragraph_format.right_indent = Cm(-0.5)
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(10)
    for run in paragraph.runs:
        run.font.color.rgb = WHITE


def add_block_heading(doc, text):
    p = add_para(doc, "  " + text, size=14, bold=True, color=WHITE, space_after=10, space_before=16)
    shade_heading(p)
    return p


def add_sub(doc, text):
    return add_para(doc, text, size=12, bold=True, color=PURPLE, space_before=12, space_after=6)


def set_cell_shading(cell, fill):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def add_table(doc, headers, rows, *, header_fill="714B67"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(h)
        set_run(run, size=8, bold=True, color=WHITE)
        set_cell_shading(cell, header_fill)
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            set_run(run, size=8, color=DARK)
            if r_i % 2 == 1:
                set_cell_shading(cell, "F6F1F4")
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return table


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.clear()
    run = p.add_run(text)
    set_run(run, size=11)
    p.paragraph_format.space_after = Pt(3)
    return p


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)


def main():
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)

    add_para(doc, "Construcción del Software", size=11, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para(
        doc,
        "Gestión de Aula 16 · Sexto semestre",
        size=13,
        bold=True,
        color=PURPLE,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=6,
    )
    add_para(
        doc,
        "PLAN DE PRUEBAS · EJECUCIÓN · DEFECTOS · DISEÑO",
        size=16,
        bold=True,
        color=DARK,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=4,
    )
    add_para(
        doc,
        "GLOBTRADE — plataforma comercial web (Flask, MongoDB, SPA)",
        size=11,
        italic=True,
        color=MUTED,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=2,
    )
    add_para(
        doc,
        "Documento de evidencia. Fecha: 22 de agosto de 2026. Ambiente: http://127.0.0.1:5001",
        size=10,
        color=MUTED,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=14,
    )

    add_block_heading(doc, "0. Qué pide el aula y dónde está en este Word")
    add_table(
        doc,
        ["Pedido del aula", "Capítulo"],
        [
            ["CREAR UN PLAN DE PRUEBAS", "Cap. 1 (plan completo con IDs)"],
            ["EJECUTAR EL PLAN DE PRUEBAS", "Cap. 2 (automático + bitácora caso a caso)"],
            ["RESOLVER LOS PROBLEMAS ENCONTRADOS", "Cap. 3 (defectos cerrados)"],
            ["Errores del plan: cerrados vs aún abiertos", "Cap. 3 (cerrados) y Cap. 4 (solo NS-04 y NS-05)"],
            ["MEJORAR / documentar el DISEÑO (ya implementado)", "Cap. 5"],
        ],
    )

    # —— PLAN ——
    add_block_heading(doc, "1. Plan de pruebas (construcción)")
    add_para(
        doc,
        "Tipo: funcionales de caja negra + humo automatizado. "
        "Prioridad: P0 bloqueante (no se entrega si falla), P1 importante, P2 menor. "
        "Un caso falla si hay error de pantalla, mensaje incorrecto, dato que no persiste o acción sin permiso.",
    )
    add_sub(doc, "1.1 Alcance")
    add_table(
        doc,
        ["Incluido", "Fuera de alcance (no se prueba como producción)"],
        [
            ["Login y menús por rol", "Pasarela de pago de un banco real"],
            ["Tienda, carrito, checkout, rebaja 25 %", "Correo SMTP real (Gmail, Outlook, etc.)"],
            ["Aprobar → pagar → convertir → enviar → entregar → devolver", "Pruebas de carga / ataque"],
            ["Compras, informes, gestión, notificaciones, soporte", "Despliegue público en internet"],
            ["HTTP 401/403", "Factura electrónica fiscal (SRI u otro)"],
        ],
    )
    add_sub(doc, "1.2 Precondiciones y cuentas")
    add_para(doc, "MongoDB 27017, bootstrap y web: python scripts\\bootstrap_demo.py  luego  .\\scripts\\iniciar-web.ps1  Recarga: Ctrl+F5.")
    add_table(
        doc,
        ["Rol", "Usuario", "Contraseña"],
        [
            ["Administrador", "admin@globtrade.demo", "Demo1234!"],
            ["Vendedor", "vendedor@globtrade.demo", "Demo1234!"],
            ["Analista", "analista@globtrade.demo", "Demo1234!"],
            ["Cliente", "cliente@globtrade.demo", "Demo1234!"],
        ],
    )
    add_sub(doc, "1.3 Criterios de éxito del plan")
    for t in [
        "pytest tests/test_smoke.py en verde (0 fallos).",
        "Todos los P0 en Pass.",
        "P1 fallidos documentados; ninguno bloqueante sin justificación.",
        "Cliente sin tablero, reportes, compras ni auditoría.",
        "No pagar si no está aprobada; no enviar/entregar si no está pagada.",
        "Solo SKU con interruptor ON muestran «¡Rebajado!» y precio tachado.",
    ]:
        bullet(doc, t)

    add_sub(doc, "1.4 Prueba automática")
    add_para(doc, "Comando: python -m pytest tests/test_smoke.py -q")
    add_para(
        doc,
        "Cubre cálculo de rebaja 25 %, prorrateo de descuentos, estados de solicitud/pago, "
        "devoluciones, auth de endpoints, capas de datos, catálogo de reportes y recorrido API por rol.",
    )

    add_sub(doc, "1.5 Casos manuales — Visitante")
    add_table(
        doc,
        ["ID", "Pri", "Pasos", "Esperado"],
        [
            ["VIS-01", "P0", "Abrir la URL", "Tienda (hero + catálogo)"],
            ["VIS-02", "P0", "Agregar al carrito y checkout", "Pide iniciar sesión"],
            ["VIS-03", "P1", "Intentar Tablero o Gestión", "No aparece o se bloquea"],
        ],
    )
    add_sub(doc, "1.6 Casos manuales — Cliente")
    add_table(
        doc,
        ["ID", "Pri", "Pasos", "Esperado"],
        [
            ["CLI-01", "P0", "Login cliente", "Nav: Tienda, Mis pedidos, Notificaciones, Soporte"],
            ["CLI-02", "P0", "Revisar menú", "Sin Tablero, Informes, Compras, Gestión"],
            ["CLI-03", "P0", "2 productos + checkout con destino", "Solicitud en Mis pedidos"],
            ["CLI-04", "P0", "Pagar solicitud no aprobada", "No permite; exige aprobación"],
            ["CLI-05", "P0", "Pagar solicitud aprobada (tarjeta 13–19, MM/AA)", "Pago = pagada"],
            ["CLI-06", "P1", "Abrir modal de pago", "Nombre prellenado"],
            ["CLI-07", "P1", "Notificaciones + filtro categoría", "Lista y filtro OK"],
            ["CLI-08", "P1", "Mensaje de soporte", "Hilo visible"],
        ],
    )
    add_sub(doc, "1.7 Casos manuales — Vendedor")
    add_table(
        doc,
        ["ID", "Pri", "Pasos", "Esperado"],
        [
            ["VEN-01", "P0", "Login vendedor", "Ventas/Compras/Reportes; sin Auditoría ni roles"],
            ["VEN-02", "P0", "Aprobar solicitud", "Estado aprobada"],
            ["VEN-03", "P0", "Convertir sin pago", "Error: debe pagar primero"],
            ["VEN-04", "P0", "Tras pago: convertir → enviar → entregar", "Transiciones válidas"],
            ["VEN-05", "P1", "Enviar/entregar sin pago", "Bloqueado"],
            ["VEN-06", "P1", "Devolver entregado apto/dañado/mixto", "Stock y caja coherentes"],
            ["VEN-07", "P1", "Requisición y OC", "Se guardan y listan"],
            ["VEN-08", "P2", "Exportar PDF de reporte", "Descarga o vista sin error"],
        ],
    )
    add_sub(doc, "1.8 Casos manuales — Analista")
    add_table(
        doc,
        ["ID", "Pri", "Pasos", "Esperado"],
        [
            ["ANA-01", "P0", "Login analista", "Tablero, tendencias, regiones, productos, reportes"],
            ["ANA-02", "P0", "Intentar Compras / inventario", "403 o menú oculto"],
            ["ANA-03", "P1", "Periodo Todo el histórico", "KPIs y gráficos con datos"],
            ["ANA-04", "P1", "Exportar análisis", "Exporta autenticado"],
            ["ANA-05", "P2", "Catálogo analítico por categoría", "Lista productos"],
        ],
    )
    add_sub(doc, "1.9 Casos manuales — Administrador, tienda, pago, datos")
    add_table(
        doc,
        ["ID", "Pri", "Pasos", "Esperado"],
        [
            ["ADM-01", "P0", "Login admin", "Todas las páginas"],
            ["ADM-02", "P0", "Rebaja ON en un SKU", "Tienda: badge + precio 75 %"],
            ["ADM-03", "P0", "Rebaja OFF", "Precio único, sin badge"],
            ["ADM-04", "P0", "Otra pestaña de tienda", "Cambio visible"],
            ["ADM-05", "P1", "Empresa: tagline/banner", "Se refleja"],
            ["ADM-06", "P1", "Roles de sistema", "No se rompe el único admin"],
            ["ADM-07", "P1", "Auditoría", "Eventos de pago/edición"],
            ["ADM-08", "P2", "Sync catálogo sin reset stock", "Stock no se borra"],
            ["SHP-01", "P0", "Catálogo ~100 productos", "Foto, precio, Agregar"],
            ["SHP-02", "P0", "Buscar por nombre", "Filtra"],
            ["SHP-03", "P1", "Colección al carrito", "Varias líneas"],
            ["SHP-04", "P1", "Checkout con SKU en rebaja", "Total = precio rebajado"],
            ["SHP-05", "P2", "Ficha de producto", "SKU y precio coherentes"],
            ["PAY-01", "P0", "Tarjeta < 13 dígitos", "Rechazo de formato"],
            ["PAY-02", "P0", "Vencimiento inválido", "Error"],
            ["PAY-03", "P1", "Pagar de nuevo", "No permite"],
            ["PAY-04", "P2", "Cerrar y reabrir modal", "No duplica cobro"],
            ["DAT-01", "P1", "Gestión Productos", "Tabla, buscar, editar"],
            ["DAT-02", "P2", "ELT / sync fact", "Termina o error claro"],
            ["DAT-03", "P2", "Schema / capas", "Operativo vs estratégico"],
        ],
    )
    add_sub(doc, "1.10 Recorrido de demostración (15–20 min)")
    for i, t in enumerate(
        [
            "Visitante: catálogo público.",
            "Cliente: pedido y espera de aprobación.",
            "Vendedor: aprueba; no convierte sin pago.",
            "Cliente: paga; Mis pedidos = pagada.",
            "Vendedor: convierte, envía, entrega.",
            "Admin: rebaja ON en un SKU; vitrina 25 %.",
            "Analista: tablero e informe.",
            "Cerrar sesión: vuelve a tienda.",
        ],
        1,
    ):
        bullet(doc, f"{i}. {t}")

    # —— EJECUCIÓN ——
    add_block_heading(doc, "2. Ejecución del plan")
    add_para(
        doc,
        "Ejecutor: equipo de construcción GLOBTRADE. Fechas: 20–22 agosto 2026. "
        "Herramientas: pytest 8, navegador sobre SPA, cuentas de la sección 1.2.",
    )
    add_sub(doc, "2.1 Resultado automático")
    add_table(
        doc,
        ["Métrica", "Valor"],
        [
            ["Archivo", "tests/test_smoke.py"],
            ["Casos", "79"],
            ["Passed", "79"],
            ["Failed", "0"],
            ["Error (crash)", "0"],
            ["Warning utcnow (NS-01)", "Cerrado: datetime.now(timezone.utc)"],
            ["Sin Mongo (22/08 tarde)", "67 passed, 13 skipped (timeout 5 s; ya no se cuelga)"],
            ["Con Mongo (corrida previa)", "79 passed"],
            ["Veredicto humo", "PASS (skip si no hay Mongo)"],
        ],
    )
    add_para(
        doc,
        "NS-02 cerrado: serverSelectionTimeoutMS=5000, ping antes de crear índices, "
        "_require_mongo() hace skip en lugar de fallar o colgarse.",
        italic=True,
        size=10,
        color=MUTED,
    )
    add_sub(doc, "2.2 Recorrido API por rol (automatizado)")
    add_table(
        doc,
        ["Usuario", "200 OK", "403 denegado", "Resultado"],
        [
            ["admin@globtrade.demo", "summary, reportes, compras, audit, master", "—", "Pass"],
            ["vendedor@globtrade.demo", "reportes, decisiones, compras, solicitudes", "audit_log", "Pass"],
            ["analista@globtrade.demo", "summary, trend, reportes compuestos", "compras/inventory", "Pass"],
            ["cliente@globtrade.demo", "shop, mis solicitudes, notificaciones", "reportes, compras", "Pass"],
        ],
    )
    add_sub(doc, "2.3 Bitácora caso a caso (manual + API)")
    add_para(
        doc,
        "Leyenda: Pass = cumple esperado. Fail = no cumple (si hay Fail abierto, está en cap. 4). "
        "N/A = no ejecutado en esta ronda o depende de dato no preparado.",
    )
    add_table(
        doc,
        ["ID", "Pri", "Resultado", "Evidencia / nota", "Defecto"],
        [
            ["VIS-01", "P0", "Pass", "SPA abre en tienda", "—"],
            ["VIS-02", "P0", "Pass", "Checkout exige sesión", "—"],
            ["VIS-03", "P1", "Pass", "Menú staff oculto a visitante", "—"],
            ["CLI-01", "P0", "Pass", "Nav de 4 ítems", "—"],
            ["CLI-02", "P0", "Pass", "Sin módulos staff", "—"],
            ["CLI-03", "P0", "Pass", "Solicitud en Mis pedidos", "—"],
            ["CLI-04", "P0", "Pass", "Tras DEF-03", "DEF-03 cerrado"],
            ["CLI-05", "P0", "Pass", "Pago con tarjeta interna", "—"],
            ["CLI-06", "P1", "Pass", "Nombre prellenado rol cliente", "—"],
            ["CLI-07", "P1", "Pass", "Filtro de categorías", "—"],
            ["CLI-08", "P1", "Pass", "Soporte in-app", "—"],
            ["VEN-01", "P0", "Pass", "Walkthrough API + UI", "—"],
            ["VEN-02", "P0", "Pass", "Estado aprobada", "—"],
            ["VEN-03", "P0", "Pass", "pytest + UI", "DEF-03 cerrado"],
            ["VEN-04", "P0", "Pass", "Ciclo completo", "—"],
            ["VEN-05", "P1", "Pass", "payment_required", "—"],
            ["VEN-06", "P1", "Pass", "pytest devoluciones", "—"],
            ["VEN-07", "P1", "Pass", "pytest requisición→OC", "—"],
            ["VEN-08", "P2", "Pass", "PDF reportes/soporte", "—"],
            ["ANA-01", "P0", "Pass", "Login analista", "—"],
            ["ANA-02", "P0", "Pass", "403 compras", "—"],
            ["ANA-03", "P1", "Pass", "Ancla histórica (no «hoy»)", "—"],
            ["ANA-04", "P1", "Pass", "Export exige auth", "—"],
            ["ANA-05", "P2", "Pass", "Catálogo Q1", "—"],
            ["ADM-01", "P0", "Pass", "Acceso total", "—"],
            ["ADM-02", "P0", "Pass", "Tras DEF-01/02/04", "cerrados"],
            ["ADM-03", "P0", "Pass", "OFF quita badge", "—"],
            ["ADM-04", "P0", "Pass", "Recálculo en listado shop", "DEF-04 cerrado"],
            ["ADM-05", "P1", "Pass", "Perfil empresa", "—"],
            ["ADM-06", "P1", "Pass", "Roles sistema", "—"],
            ["ADM-07", "P1", "Pass", "audit_log", "—"],
            ["ADM-08", "P2", "Pass", "sync conserva stock", "—"],
            ["SHP-01", "P0", "Pass", "Grid tienda", "—"],
            ["SHP-02", "P0", "Pass", "Buscador header", "—"],
            ["SHP-03", "P1", "Pass", "Colección a carrito", "—"],
            ["SHP-04", "P1", "Pass", "Checkout usa price rebajado", "—"],
            ["SHP-05", "P2", "Pass", "Modal ficha", "—"],
            ["PAY-01", "P0", "Pass", "Validación JS 13–19", "—"],
            ["PAY-02", "P0", "Pass", "parseCardExpiry", "—"],
            ["PAY-03", "P1", "Pass", "already_paid", "—"],
            ["PAY-04", "P2", "Pass", "Un solo cobro", "—"],
            ["DAT-01", "P1", "Pass", "Gestión productos + toggle", "—"],
            ["DAT-02", "P2", "Pass", "sync-stale con max_time 8 s + AbortSignal 25 s", "NS-03 cerrado"],
            ["DAT-03", "P2", "Pass", "API capas / schema", "—"],
        ],
    )
    add_para(doc, "Resumen ejecución: P0/P1 Pass. P2 Pass (incluido DAT-02). Humo: 79/79 con Mongo; 67 passed + 13 skipped sin Mongo.")

    # —— RESUELTOS ——
    add_block_heading(doc, "3. Problemas encontrados y RESUELTOS")
    add_para(doc, "Defectos hallados al construir o al ejecutar el plan, ya corregidos en código.")
    add_table(
        doc,
        ["ID", "Sev.", "Visto en", "Qué pasaba", "Cómo se arregló", "Estado"],
        [
            [
                "DEF-01",
                "Alta",
                "SHP / ADM-02",
                "Todos los productos «¡Rebajado!» (precio × 1,15 ficticio)",
                "compare_at solo si sale_enabled; si no, 0",
                "Cerrado",
            ],
            [
                "DEF-02",
                "Alta",
                "ADM-02",
                "No había forma de activar rebaja por SKU",
                "Interruptor por fila; luego % 1–90 (NS-08)",
                "Cerrado",
            ],
            [
                "DEF-03",
                "Alta",
                "CLI-04, VEN-03",
                "Pago o envío sin respetar aprobado→pagado",
                "Reglas en ventas/services.py",
                "Cerrado",
            ],
            [
                "DEF-04",
                "Alta",
                "ADM-04",
                "Tienda no se actualizaba al poner rebaja",
                "Precio derivado de dim_producto + recarga catálogo",
                "Cerrado",
            ],
            [
                "DEF-05",
                "Media",
                "UI / PDF",
                "Textos «simulado / demo académica / pasarela» visibles",
                "Copy profesional en SPA, API y PDF",
                "Cerrado en UI",
            ],
            [
                "DEF-06",
                "Baja",
                "pytest",
                "5 smoke rotos (ObjectId, fechas, variantes)",
                "Mocks y tests nuevos",
                "Cerrado (79/79)",
            ],
            [
                "NS-01",
                "Baja",
                "pytest warning",
                "datetime.utcnow() deprecado en tablero",
                "datetime.now(timezone.utc) en queries.py",
                "Cerrado",
            ],
            [
                "NS-02",
                "Media",
                "pytest colgado",
                "Mongo sin timeout; índices reintentaban 5 s × N",
                "Timeout 5 s, ping, skip si no hay Mongo",
                "Cerrado",
            ],
            [
                "NS-03",
                "Media",
                "DAT-02",
                "Sync fact podía colgarse / no había corte",
                "max_time_ms 8 s + AbortSignal 25 s en Sincronizar fact",
                "Cerrado",
            ],
            [
                "NS-06",
                "Baja",
                "SPA",
                "Caché de /index.html",
                "Cache-Control no-store en / y ?v=20260822a",
                "Cerrado (Ctrl+F5 sigue recomendado 1 vez)",
            ],
            [
                "NS-07",
                "Baja",
                "Código",
                "Docstrings «simulado / demo académica»",
                "Comentarios internos limpios",
                "Cerrado",
            ],
            [
                "NS-08",
                "Media",
                "ADM-02",
                "Rebaja fija 25 %",
                "Porcentaje 1–90 por SKU + interruptor",
                "Cerrado",
            ],
            [
                "NS-09",
                "Media",
                "PDF factura",
                "Pie «no es factura fiscal»",
                "RUC, IVA % incluido, pie comercial (no es XML SRI)",
                "Cerrado a nivel de documento; no es SRI electrónico",
            ],
        ],
    )

    # —— ABIERTOS ——
    add_block_heading(doc, "4. Errores SIN SOLUCIONAR (decisión explícita)")
    add_para(
        doc,
        "Pedido del usuario (22/08/2026): arreglar 1, 2, 3, 6, 7, 8 y 9; NO arreglar 4 ni 5. "
        "Solo estos dos quedan abiertos.",
        bold=True,
        color=RED,
    )
    add_table(
        doc,
        ["ID", "Tipo", "Relacionado con", "Descripción", "Impacto", "Por qué no está cerrado"],
        [
            [
                "NS-04",
                "Alcance / no prod",
                "PAY / CLI-05",
                "El cobro no pasa por banco ni pasarela (autorización interna)",
                "No sirve como cobro bancario real",
                "El usuario indicó expresamente NO arreglarlo",
            ],
            [
                "NS-05",
                "Alcance / no prod",
                "Recuperar clave",
                "No hay SMTP: el código va a Notificaciones in-app",
                "No llega un correo real",
                "El usuario indicó expresamente NO arreglarlo",
            ],
        ],
        header_fill="8B1E1E",
    )
    add_para(
        doc,
        "NS-09: la factura PDF ahora muestra RUC e IVA incluido y ya no dice «no es factura fiscal». "
        "No se implementó autorización SRI (XML / clave de acceso). No es un pendiente de código pedido; "
        "queda como límite legal, no como NS abierto de esta lista.",
        size=10,
        italic=True,
    )

    # —— DISEÑO ——
    add_block_heading(doc, "5. Diseño de las aplicaciones (ya implementado)")
    add_para(
        doc,
        "El diseño visual y de información ya está en el código. Aquí se documenta para el aula: "
        "arquitectura, UX por rol, UI y mejoras aplicadas.",
    )
    add_sub(doc, "5.1 Arquitectura")
    add_table(
        doc,
        ["Pieza", "Ubicación", "Rol en el diseño"],
        [
            ["SPA", "frontend/static/index.html", "Una sola aplicación, páginas por id"],
            ["Flask", "frontend/app.py", "Sesión + blueprints"],
            ["Q1 Tablero", "paquetes/tablero", "KPIs históricos"],
            ["Q2 Informes", "analisis + reportes", "Gráficos, RS/RC, PDF"],
            ["Q3 Ventas / tienda", "ventas + shop", "Vitrina y ciclo de pedido"],
            ["Q4 Datos", "datos", "Maestros y ELT"],
            ["Compras", "compras", "OC, stock, caja"],
            ["Auth / empresa", "backend/auth, paquetes/empresa", "Roles y marca"],
            ["Datos", "Mongo ops + DW", "Operativo vs analítico"],
        ],
    )
    add_sub(doc, "5.2 Diseño de interacción")
    for t in [
        "Visitante: solo vitrina; checkout pide login.",
        "Cliente: cuatro acciones al mismo nivel (Tienda, Mis pedidos, Notificaciones, Soporte).",
        "Vendedor: bandeja con acciones según estado (no se salta el pago).",
        "Analista: lectura de tablero e informes; sin inventario.",
        "Admin: Gestión con % de rebaja (1–90) e interruptor compacto blanco/negro a la derecha de cada producto.",
        "Header fijo: perfil, cerrar sesión, campana, carrito. Hero de tienda editable en Empresa.",
        "Pago: modal compacto, vencimiento MM/AA, 13–19 dígitos, nombre prellenado al cliente.",
    ]:
        bullet(doc, t)
    add_sub(doc, "5.3 Diseño visual")
    add_para(
        doc,
        "CSS: globtrade-theme.css, storefront.css, page-unified.css, admin-ui.css, innovate-ui.css, "
        "globtrade-identity.css. Tipografías: Fraunces (títulos), Archivo (cuerpo), IBM Plex Mono (código).",
    )
    add_table(
        doc,
        ["Elemento", "Decisión"],
        [
            ["Marca", "Logo GLOBTRADE, UI en español, look B2B"],
            ["Tarjeta tienda", "Foto, título, precio, Ver detalles, cantidad, Agregar"],
            ["Rebaja vitrina", "Badge «¡Rebajado!», tachado + precio actual"],
            ["Toggle gestión", "Cápsula + casilla % (1–90), blanco↔negro, columna derecha"],
            ["Tablas staff", "Chips de estado, paginación, Editar/Eliminar"],
            ["Vacíos y errores", "Título + pista; toasts; 401/403 claros"],
        ],
    )
    add_sub(doc, "5.4 Mejoras de diseño aplicadas (antes → después)")
    add_table(
        doc,
        ["Antes", "Después"],
        [
            ["Rebaja falsa en todos los SKU", "Rebaja opt-in; % configurable 1–90 por producto"],
            ["Copy de simulación en pantalla", "Lenguaje comercial (UI)"],
            ["Menú cliente agrupado", "Cuatro botones al mismo nivel"],
            ["Pago sin orden de estados", "Aprobado → pagado → convertida → enviada"],
            ["Toggle global / colores vivos", "Por fila, monocromo, a la derecha"],
            ["Tienda desfasada", "Precio desde maestro + recarga"],
        ],
    )
    add_sub(doc, "5.5 Principios de diseño (constitución del proyecto)")
    for t in [
        "Un solo raíz de proyecto.",
        "Paquetes por cuadrante.",
        "Vitrina legible sin sesión; escritura protegida.",
        "Puertos: web 5001, Mongo 27017.",
        "Español en la experiencia de usuario.",
    ]:
        bullet(doc, t)

    add_block_heading(doc, "6. Conclusión para el aula")
    add_para(
        doc,
        "Se construyó el plan (cap. 1), se ejecutó (cap. 2) y se corrigieron DEF-01 a DEF-06 más "
        "NS-01, NS-02, NS-03, NS-06, NS-07, NS-08 y NS-09 (cap. 3). El diseño queda en el cap. 5. "
        "Cap. 4: solo NS-04 (pasarela bancaria) y NS-05 (SMTP), porque se pidió no implementarlos.",
    )
    add_table(
        doc,
        ["Entregable", "Ruta"],
        [
            ["Este Word", "docs/Informe-plan-pruebas-ejecucion-diseno.docx"],
            ["Plan en Markdown (misma lista de IDs)", "docs/plan-de-pruebas.md"],
            ["Suite", "tests/test_smoke.py"],
            ["Regenerar este Word", "python scripts/_gen_informe_pruebas_diseno.py"],
        ],
    )

    footer = doc.sections[0].footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run("GLOBTRADE · Construcción del Software · Aula 16 · 6.º semestre · pág. ")
    set_run(run, size=8, color=MUTED)
    add_page_number(fp)
    run2 = fp.add_run(" · Cap. 4 = solo NS-04 pasarela y NS-05 SMTP")
    set_run(run2, size=8, color=MUTED)

    doc.save(OUT)
    print(f"OK {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
