"""Genera Plan de Negocios GLOBTRADE alineado al proyecto vicuna."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

OUT = Path(r"c:\Users\redsito\Downloads\Plan_Negocios_GlobalSales.docx")
OUT_PROJECT = Path(__file__).resolve().parents[1] / "docs" / "Plan_Negocios_GLOBTRADE.docx"


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(11)


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
    for r_idx, row in enumerate(rows, start=1):
        for c_idx, val in enumerate(row):
            table.rows[r_idx].cells[c_idx].text = val


def build() -> Document:
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("PLAN DE NEGOCIOS")
    r.bold = True
    r.font.size = Pt(18)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("GLOBTRADE S.A.")
    r2.bold = True
    r2.font.size = Pt(16)

    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub2.add_run("Plataforma web de gestión y análisis de ventas internacionales").font.size = Pt(12)

    sub3 = doc.add_paragraph()
    sub3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub3.add_run("Proyecto escolar  |  2025–2026").font.size = Pt(11)

    doc.add_paragraph()

    add_heading(doc, "1. Descripción del producto", 1)
    add_para(
        doc,
        "GLOBTRADE S.A. es una aplicación web para centralizar, consultar y analizar un "
        "gran volumen de ventas internacionales. El sistema importa datos desde CSV, los "
        "procesa mediante un pipeline ELT (CSV → Parquet → MongoDB) y expone un dashboard "
        "con indicadores (KPIs), gráficos y exploración de tablas maestras (dimensiones) "
        "y hechos analíticos.",
    )
    add_table(
        doc,
        ["Campo", "Detalle"],
        [
            ["Nombre comercial", "GLOBTRADE S.A. (proyecto: vicuna)"],
            ["Tipo", "Aplicación web de analítica y gestión de ventas"],
            ["Base de datos", "MongoDB 7 — base globtrade_dw (~200.000 registros en sales_records)"],
            ["Usuarios objetivo", "Analistas de ventas y administradores (roles planificados v4.0)"],
            ["Plataforma", "Navegador web (Chrome, Firefox, Edge); despliegue local con Docker Desktop"],
        ],
    )

    add_heading(doc, "2. Problema que resuelve", 1)
    add_para(doc, "Gestionar cientos de miles de filas en Excel o CSV implica:")
    for item in [
        "Dificultad para filtrar y buscar por región, país, producto o canal.",
        "Ausencia de visualizaciones automáticas de tendencias y comparativos.",
        "Riesgo de errores al editar datos manualmente.",
        "Limitaciones para varios usuarios trabajando en paralelo.",
        "Falta de KPIs consolidados (ingresos, costos, utilidad, margen).",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    add_para(
        doc,
        "GLOBTRADE centraliza la información en MongoDB, aplica un modelo dimensional "
        "(tablas maestras + hechos) y ofrece un dashboard accesible vía web.",
    )

    add_heading(doc, "3. Funcionalidades del sistema", 1)

    add_heading(doc, "Módulo 1 — Dashboard principal", 2)
    for item in [
        "KPIs: total de pedidos, ingresos, utilidad, costos y margen promedio.",
        "Gráficos por región, canal (Online/Offline), prioridad y top países.",
        "Tendencia mensual de ingresos y utilidad.",
        "Tabla paginada de registros con filtros (producto, canal, prioridad).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Módulo 2 — Tablas maestras (dimensiones)", 2)
    for item in [
        "Exploración de 10 catálogos/dimensiones: región, país, categoría, producto, canal, prioridad, cliente, tiempo, etc.",
        "Conteo de registros por colección y búsqueda en columnas.",
        "Construcción del modelo desde sales_records (botón «Construir tablas maestras»).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Módulo 3 — Gestión y consulta de ventas", 2)
    for item in [
        "Listado de órdenes/ventas con paginación server-side.",
        "Filtros por país, tipo de producto, canal y prioridad.",
        "API CRUD (FastAPI) sobre dimensiones y hechos para mantenimiento.",
        "Generación adicional de registros en sales_records (planificado / en integración).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Módulo 4 — Reportes y exportación", 2)
    for item in [
        "Resúmenes por región y producto en pantalla (implementado).",
        "Exportación a PDF/Excel y reportes programados (roadmap v3.0).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "4. Stack tecnológico (implementado)", 1)
    add_table(
        doc,
        ["Capa", "Tecnología", "Función"],
        [
            ["Frontend / Dashboard", "Flask + HTML/CSS/JS (Chart.js)", "UI en puerto 5000"],
            ["API", "FastAPI + Uvicorn", "CRUD REST en puerto 8000"],
            ["Datos", "MongoDB 7 (Docker)", "Almacén analítico globtrade_dw"],
            ["ELT", "Python (pandas, pyarrow, pymongo)", "CSV → Parquet → MongoDB → transformaciones"],
            ["Contenedores", "Docker Compose", "mongo, web, api, perfil etl-mongo"],
            ["Configuración", "pydantic-settings + .env", "MONGO_URI, MONGO_DB, rutas de datos"],
        ],
    )
    add_para(
        doc,
        "Nota: el prototipo inicial del plan contemplaba React, Node.js y PostgreSQL; "
        "la implementación actual prioriza Python unificado, MongoDB y Docker por volumen "
        "de datos y flexibilidad del esquema.",
        bold=False,
    )

    add_heading(doc, "5. Modelo de datos", 1)
    add_para(doc, "5.1 Colección principal (staging)")
    add_para(
        doc,
        "sales_records: dataset de ventas con campos order_id, region, country, item_type, "
        "sales_channel, order_priority, order_date, ship_date, units_sold, unit_price, "
        "unit_cost, total_revenue, total_cost, total_profit.",
    )

    add_para(doc, "5.2 Tablas maestras (dimensiones — 10 catálogos)")
    add_table(
        doc,
        ["Colección MongoDB", "Rol"],
        [
            ["dim_region", "Regiones comerciales"],
            ["dim_pais", "Países"],
            ["dim_categoria", "Categorías de producto"],
            ["dim_producto", "Productos"],
            ["dim_canal", "Canales Online/Offline"],
            ["dim_prioridad", "Prioridades C/H/M/L"],
            ["dim_cliente", "Clientes"],
            ["dim_tiempo", "Calendario / fechas"],
            ["product_categories", "Catálogo espejo (SQL)"],
            ["products", "Catálogo espejo (SQL)"],
        ],
    )

    add_para(doc, "5.3 Hechos y agregados")
    add_table(
        doc,
        ["Colección", "Rol"],
        [
            ["fact_ventas", "Tabla de hechos analíticos (venta_id, IDs de dimensión, métricas)"],
            ["orders / order_lines", "Modelo transaccional derivado del ELT"],
            ["monthly_kpis", "KPIs mensuales agregados"],
        ],
    )

    add_heading(doc, "6. Plan de desarrollo", 1)
    add_table(
        doc,
        ["Fase", "Versión", "Estado", "Funcionalidades"],
        [
            ["Fase 1 — Base", "v1.0", "Completada", "ELT, MongoDB, carga CSV/Parquet, sales_records"],
            ["Fase 2 — Visualización", "v2.0", "Completada", "Dashboard KPIs, gráficos, tablas maestras"],
            ["Fase 3 — Consulta avanzada", "v2.5", "Parcial", "Filtros, paginación, API CRUD dimensiones/hechos"],
            ["Fase 4 — Usuarios", "v4.0", "Pendiente", "Autenticación y roles (admin / analista)"],
            ["Fase 5 — Integración", "v5.0", "Pendiente", "API documentada, exportación, alertas de margen"],
        ],
    )

    add_heading(doc, "7. Plan de crecimiento", 1)
    add_heading(doc, "Corto plazo (completado / en curso)", 2)
    for item in [
        "200.000 registros en sales_records para pruebas de escala.",
        "Dashboard operativo con Docker Desktop.",
        "Modelo dimensional construido desde el ELT.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Mediano plazo", 2)
    for item in [
        "Exportación PDF/Excel de reportes filtrados.",
        "Roles: administrador (CRUD) vs analista (solo lectura).",
        "Alertas por productos con margen bajo.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "Largo plazo", 2)
    for item in [
        "API REST documentada (OpenAPI) para integraciones.",
        "Predicción de ventas con series históricas.",
        "Conexión con Power BI o herramientas externas.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_heading(doc, "8. Insights clave de los datos", 1)
    add_para(
        doc,
        "Los indicadores exactos dependen del corte del dataset cargado. Con ~200.000 "
        "registros en sales_records, el dashboard permite identificar:",
    )
    add_table(
        doc,
        ["Indicador", "Uso en GLOBTRADE"],
        [
            ["Ingresos y utilidad totales", "KPIs en dashboard (/api/summary)"],
            ["Rendimiento por región", "Gráfico de barras por región"],
            ["Canal Online vs Offline", "Gráfico de distribución por canal"],
            ["Productos y categorías", "Ranking por item_type y tablas maestras"],
            ["Prioridades de pedido", "Desglose C/H/M/L"],
            ["Cobertura geográfica", "Conteo de países distintos"],
        ],
    )
    add_para(
        doc,
        "Ejemplo de hallazgos típicos en datasets similares (referencia 100k): Cosmetics "
        "y Clothes con alto margen; canales Online/Offline equilibrados; productos como "
        "Meat con margen bajo a revisar. Recalcular siempre sobre el dataset activo en MongoDB.",
    )

    add_heading(doc, "9. Infraestructura y despliegue", 1)
    for item in [
        "Docker Compose: servicios globtrade-mongo (27017), globtrade-web (5000), globtrade-api (8000).",
        "Comando ELT: docker compose --profile etl-mongo run --rm etl-mongo.",
        "Variables: MONGO_URI=mongodb://mongo:27017, MONGO_DB=globtrade_dw.",
        "Repositorio: C:\\vicuna (proyecto unificado Kiro + MongoDB + web).",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph()
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    foot.add_run("GLOBTRADE S.A. — Proyecto escolar 2025–2026").italic = True

    return doc


def main() -> None:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    OUT_PROJECT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_PROJECT)
    print(f"Guardado: {OUT}")
    print(f"Copia:  {OUT_PROJECT}")


if __name__ == "__main__":
    main()
