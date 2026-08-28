# -*- coding: utf-8 -*-
"""Informes compuestos RC-01…RC-13 consultados exclusivamente en ClickHouse."""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

from shared.clickhouse import ensure_database_and_schema, ping_clickhouse, query_rows
from paquetes.tablero import catalogo_nombres as nom


COMPLEX_REPORTS: list[dict[str, Any]] = [
    {"id": "RC-01", "name": "Ventas por mes y categoría", "objetivo": "OT1, OT7, OT10, OT12", "para_que": "Ver la evolución de ingresos, utilidad y stock por categoría.", "quien": "Gerencia, analista", "columns": ["mes", "categoria", "pedidos", "unidades", "ingresos", "utilidad", "stock_actual"], "chart": {"type": "line", "x": "mes", "series": ["ingresos", "utilidad"], "group": "categoria"}},
    {"id": "RC-02", "name": "Productos más y menos vendidos", "objetivo": "OT7, OT10, OT12", "para_que": "Detectar productos líderes y rezagados por ingresos, cruzados con inventario.", "quien": "Gerencia comercial, analista", "columns": ["ranking", "producto", "categoria", "unidades", "ingresos", "stock_actual", "grupo"], "chart": {"type": "bar", "x": "producto", "series": ["ingresos"], "group": "grupo"}},
    {"id": "RC-03", "name": "Ventas frente a compras recibidas", "objetivo": "OT4", "para_que": "Comparar, dentro del mismo periodo, ventas y compras recibidas.", "quien": "Compras, gerencia", "columns": ["mes", "ventas", "compras", "diferencia"], "chart": {"type": "bar", "x": "mes", "series": ["ventas", "compras", "diferencia"]}},
    {"id": "RC-04", "name": "Rotación y cobertura de inventario por categoría", "objetivo": "OT3", "para_que": "Relacionar ventas con el inventario disponible y detectar riesgo.", "quien": "Inventario", "columns": ["categoria", "unidades_vendidas", "stock_actual", "rotacion_aprox", "dias_cobertura"], "chart": {"type": "bar", "x": "categoria", "series": ["unidades_vendidas", "stock_actual"]}},
    {"id": "RC-05", "name": "Cumplimiento logístico por región", "objetivo": "OT5", "para_que": "Medir tiempo promedio, cumplimiento e ingresos asociados por región.", "quien": "Logística", "columns": ["region", "pedidos", "dias_promedio", "mediana_dias", "cumplimiento_pct", "ingresos"], "chart": {"type": "bar", "x": "region", "series": ["dias_promedio", "mediana_dias"]}},
    {"id": "RC-06", "name": "Uso y rentabilidad de cupones", "objetivo": "OT6, OT9", "para_que": "Medir ingresos, descuento y resultado de promociones.", "quien": "Gerencia comercial", "columns": ["cupon", "usos", "ingresos_con_cupon", "descuento_total", "ingreso_neto", "activo"], "chart": {"type": "bar", "x": "cupon", "series": ["ingresos_con_cupon", "descuento_total", "ingreso_neto"]}},
    {"id": "RC-07", "name": "Margen por categoría en el tiempo", "objetivo": "OT2, OT12", "para_que": "Comparar utilidad, margen e inventario por categoría y mes.", "quien": "Gerencia, analista", "columns": ["mes", "categoria", "ingresos", "costos", "utilidad", "margen_pct", "stock_actual"], "chart": {"type": "line", "x": "mes", "series": ["margen_pct"], "group": "categoria"}},
    {"id": "RC-08", "name": "Estado de la carga analítica", "objetivo": "OT11, OT12", "para_que": "Comprobar carga, cobertura y consistencia entre tablas ClickHouse.", "quien": "Administración, analista", "columns": ["indicador", "valor", "estado"], "chart": {"type": "status", "x": "indicador", "series": ["valor"]}},
    {"id": "RC-09", "name": "Compras mayoristas por proveedor", "objetivo": "OT4, OT12", "para_que": "Identificar proveedores con más compras y su utilidad asociada.", "quien": "Gerencia, compras", "columns": ["proveedor", "compras", "ordenes", "utilidad", "participacion_pct", "ticket_promedio"], "chart": {"type": "bar", "x": "proveedor", "series": ["compras"]}},
    {"id": "RC-10", "name": "Dependencia estratégica por proveedor", "objetivo": "OT4, OT12", "para_que": "Detectar concentración de abastecimiento y riesgo por dependencia.", "quien": "Gerencia, compras", "columns": ["proveedor", "compras", "participacion_pct", "riesgo", "decision"], "chart": {"type": "bar", "x": "proveedor", "series": ["participacion_pct"]}},
    {"id": "RC-11", "name": "Rentabilidad por proveedor", "objetivo": "OT2, OT4, OT12", "para_que": "Saber de qué proveedores salen los productos que dejan más utilidad y cuánto se les compra.", "quien": "Gerencia, compras, analista", "columns": ["proveedor", "pedidos", "unidades", "compras", "ingresos", "costos", "utilidad", "margen_pct"], "chart": {"type": "bar", "x": "proveedor", "series": ["utilidad", "ingresos"]}},
    {"id": "RC-12", "name": "Compras vs utilidad por proveedor", "objetivo": "OT4, OT12", "para_que": "Comparar cuánto se invierte comprando a cada proveedor frente a la utilidad generada por sus productos.", "quien": "Gerencia, compras", "columns": ["proveedor", "compras", "ingresos", "utilidad", "retorno_pct", "decision"], "chart": {"type": "bar", "x": "proveedor", "series": ["compras", "utilidad"]}},
    {"id": "RC-13", "name": "Productos más rentables por proveedor", "objetivo": "OT2, OT4, OT10", "para_que": "Encontrar qué productos conviene negociar, impulsar o reponer según proveedor y stock.", "quien": "Gerencia comercial, compras", "columns": ["proveedor", "producto", "categoria", "stock_actual", "ingresos", "utilidad", "margen_pct", "decision"], "chart": {"type": "bar", "x": "producto", "series": ["utilidad"], "group": "proveedor"}},
]
COMPLEX_BY_ID = {report["id"]: report for report in COMPLEX_REPORTS}


def _meta(report: dict[str, Any]) -> dict[str, Any]:
    return {**report, "tipo": "compuesto", "data_layer": "clickhouse", "source_tables": _SOURCE_TABLES.get(report["id"], [])}


_SOURCE_TABLES: dict[str, list[str]] = {
    "RC-01": ["fact_sales", "inventory_snapshot"],
    "RC-02": ["fact_sales", "inventory_snapshot"],
    "RC-03": ["fact_sales", "fact_purchases"],
    "RC-04": ["fact_sales", "inventory_snapshot"],
    "RC-05": ["fact_logistics", "fact_sales"],
    "RC-06": ["fact_sales", "coupon_catalog"],
    "RC-07": ["fact_sales", "inventory_snapshot"],
    "RC-08": ["etl_runs", "fact_sales", "fact_purchases", "inventory_snapshot", "fact_logistics"],
    "RC-09": ["fact_purchases", "fact_sales"],
    "RC-10": ["fact_purchases", "fact_sales"],
    "RC-11": ["fact_sales", "fact_purchases"],
    "RC-12": ["fact_sales", "fact_purchases"],
    "RC-13": ["fact_sales", "inventory_snapshot"],
}


def list_complex_catalog() -> list[dict[str, Any]]:
    return [_meta(report) for report in COMPLEX_REPORTS]


def _localize_category_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compatibilidad para consumidores antiguos del catálogo de nombres."""
    return [
        {**row, "categoria": nom.category_label_from_name(row.get("categoria"))}
        if "categoria" in row else dict(row)
        for row in rows
    ]


def _filters(filters: dict[str, Any], alias: str = "") -> tuple[str, dict[str, Any]]:
    prefix = f"{alias}." if alias else ""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    if filters.get("start"):
        clauses.append(f"{prefix}sale_date >= {{start:Date}}")
        params["start"] = date.fromisoformat(str(filters["start"])[:10])
    if filters.get("end"):
        clauses.append(f"{prefix}sale_date <= {{end:Date}}")
        params["end"] = date.fromisoformat(str(filters["end"])[:10])
    for key in ("category", "region", "channel"):
        if filters.get(key):
            clauses.append(f"{prefix}{key} = {{{key}:String}}")
            params[key] = str(filters[key])
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _sales_query(sql: str, limit: int, filters: dict[str, Any], alias: str = "") -> list[dict[str, Any]]:
    where, params = _filters(filters, alias)
    params["limit"] = limit
    return query_rows(sql.replace("/*filters*/", where), params)


def rc01(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters, "fs")
    params["limit"] = limit
    return query_rows("""
      WITH stock AS (
        SELECT category categoria, round(sum(stock),2) stock_actual
        FROM inventory_snapshot FINAL GROUP BY categoria
      )
      SELECT formatDateTime(toStartOfMonth(fs.sale_date), '%Y-%m') mes, fs.category categoria,
             uniqExact(fs.order_id) pedidos, round(sum(fs.units), 2) unidades,
             round(sum(fs.revenue), 2) ingresos, round(sum(fs.profit), 2) utilidad,
             ifNull(any(stock.stock_actual), 0) stock_actual
      FROM fact_sales fs LEFT JOIN stock ON fs.category=stock.categoria
      WHERE 1 /*filters*/ GROUP BY mes, categoria
      ORDER BY mes, ingresos DESC LIMIT {limit:UInt32}
    """.replace("/*filters*/", where), params)


def rc02(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters)
    params["limit"] = min(max(limit // 2, 5), 20)
    return query_rows("""
      WITH inv AS (
        SELECT product_id, round(sum(stock),2) stock_actual
        FROM inventory_snapshot FINAL GROUP BY product_id
      ), totals AS (
        SELECT product_id, product producto, category categoria, sum(units) unidades, round(sum(revenue), 2) ingresos
        FROM fact_sales WHERE 1 /*filters*/ GROUP BY product_id, producto, categoria
      ), ranked AS (
        SELECT totals.producto producto, totals.categoria categoria, totals.unidades unidades,
               totals.ingresos ingresos, ifNull(any(inv.stock_actual),0) stock_actual,
               row_number() OVER (ORDER BY ingresos DESC) ranking_top,
               row_number() OVER (ORDER BY ingresos ASC) ranking_bottom
        FROM totals LEFT JOIN inv ON totals.product_id=inv.product_id
        GROUP BY producto, categoria, unidades, ingresos
      )
      SELECT if(ranking_top <= {limit:UInt32}, ranking_top, ranking_bottom) ranking,
             producto, categoria, round(unidades, 2) unidades, ingresos, stock_actual,
             if(ranking_top <= {limit:UInt32}, 'Más vendidos', 'Menos vendidos') grupo
      FROM ranked WHERE ranking_top <= {limit:UInt32} OR ranking_bottom <= {limit:UInt32}
      ORDER BY grupo, ranking
    """.replace("/*filters*/", where), params)


def rc03(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    sales_date = purchase_date = ""
    if filters.get("start"):
        params["start"] = date.fromisoformat(str(filters["start"])[:10]); sales_date += " AND sale_date >= {start:Date}"; purchase_date += " AND purchase_date >= {start:Date}"
    if filters.get("end"):
        params["end"] = date.fromisoformat(str(filters["end"])[:10]); sales_date += " AND sale_date <= {end:Date}"; purchase_date += " AND purchase_date <= {end:Date}"
    return query_rows(f"""
      WITH s AS (SELECT toStartOfMonth(sale_date) m, sum(revenue) ventas FROM fact_sales WHERE 1 {sales_date} GROUP BY m),
           p AS (SELECT toStartOfMonth(purchase_date) m, sum(amount) compras FROM fact_purchases
                 WHERE lowerUTF8(status) IN ('recibida','recibido','received','parcial') {purchase_date} GROUP BY m),
           months AS (SELECT m FROM s UNION DISTINCT SELECT m FROM p)
      SELECT formatDateTime(months.m, '%Y-%m') mes, round(ifNull(ventas,0),2) ventas,
             round(ifNull(compras,0),2) compras, round(ifNull(ventas,0)-ifNull(compras,0),2) diferencia
      FROM months LEFT JOIN s ON months.m=s.m LEFT JOIN p ON months.m=p.m
      ORDER BY mes LIMIT {{limit:UInt32}}
    """, params)


def rc04(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters); params["limit"] = limit
    return query_rows("""
      WITH sold AS (SELECT category categoria, sum(units) unidades, dateDiff('day', min(sale_date), max(sale_date))+1 dias
                    FROM fact_sales WHERE 1 /*filters*/ GROUP BY categoria),
           stock AS (SELECT category categoria, sum(stock) existencias FROM inventory_snapshot FINAL GROUP BY categoria),
           categories AS (SELECT categoria FROM sold UNION DISTINCT SELECT categoria FROM stock)
      SELECT categories.categoria categoria, round(ifNull(unidades,0),2) unidades_vendidas,
             round(ifNull(existencias,0),2) stock_actual,
             round(if(existencias>0, unidades/existencias, 0),2) rotacion_aprox,
             round(if(unidades>0, existencias/(unidades/greatest(dias,1)), 0),1) dias_cobertura
      FROM categories LEFT JOIN sold ON categories.categoria=sold.categoria
      LEFT JOIN stock ON categories.categoria=stock.categoria
      ORDER BY rotacion_aprox DESC LIMIT {limit:UInt32}
    """.replace("/*filters*/", where), params)


def rc05(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    clauses, params = [], {"limit": limit}
    if filters.get("start"):
        clauses.append("created_date >= {start:Date}"); params["start"] = date.fromisoformat(str(filters["start"])[:10])
    if filters.get("end"):
        clauses.append("created_date <= {end:Date}"); params["end"] = date.fromisoformat(str(filters["end"])[:10])
    if filters.get("region"):
        clauses.append("region = {region:String}"); params["region"] = str(filters["region"])
    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return query_rows(f"""
      WITH sales_region AS (
        SELECT region, round(sum(revenue),2) ingresos
        FROM fact_sales GROUP BY region
      )
      SELECT l.region region, count() pedidos, round(avg(l.days_to_ship),1) dias_promedio,
             round(quantileExact(0.5)(days_to_ship),1) mediana_dias,
             round(countIf(l.days_to_ship <= 3)/count()*100,1) cumplimiento_pct,
             ifNull(any(sales_region.ingresos),0) ingresos
      FROM fact_logistics l LEFT JOIN sales_region ON l.region=sales_region.region
      WHERE l.days_to_ship IS NOT NULL {where}
      GROUP BY region ORDER BY dias_promedio DESC LIMIT {{limit:UInt32}}
    """, params)


def rc06(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters, "s"); params["limit"] = limit
    return query_rows("""
      SELECT s.coupon cupon, uniqExact(s.order_id) usos, round(sum(s.revenue),2) ingresos_con_cupon,
             round(sum(s.discount),2) descuento_total, round(sum(s.revenue)-sum(s.discount),2) ingreso_neto,
             ifNull(any(c.active), false) activo
      FROM fact_sales s LEFT JOIN coupon_catalog c ON s.coupon=c.code
      WHERE s.coupon != '' /*filters*/ GROUP BY cupon ORDER BY usos DESC LIMIT {limit:UInt32}
    """.replace("/*filters*/", where), params)


def rc07(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters, "fs")
    params["limit"] = limit
    return query_rows("""
      WITH stock AS (
        SELECT category categoria, round(sum(stock),2) stock_actual
        FROM inventory_snapshot FINAL GROUP BY categoria
      )
      SELECT formatDateTime(toStartOfMonth(fs.sale_date), '%Y-%m') mes, fs.category categoria,
             round(sum(fs.revenue),2) ingresos, round(sum(fs.cost),2) costos, round(sum(fs.profit),2) utilidad,
             round(if(sum(fs.revenue)>0,sum(fs.profit)/sum(fs.revenue)*100,0),2) margen_pct,
             ifNull(any(stock.stock_actual),0) stock_actual
      FROM fact_sales fs LEFT JOIN stock ON fs.category=stock.categoria
      WHERE 1 /*filters*/ GROUP BY mes,categoria ORDER BY mes,categoria LIMIT {limit:UInt32}
    """.replace("/*filters*/", where), params)


def rc08(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    rows = query_rows("SELECT loaded_at,status,rows_sales,rows_purchases,rows_inventory,rows_logistics FROM etl_runs ORDER BY loaded_at DESC LIMIT 1")
    coverage = query_rows("""
      SELECT
        (SELECT count() FROM fact_sales) sales_rows,
        (SELECT count() FROM fact_purchases) purchase_rows,
        (SELECT count() FROM inventory_snapshot FINAL) inventory_rows,
        (SELECT count() FROM fact_logistics) logistics_rows,
        (SELECT uniqExact(product_id) FROM fact_sales WHERE product_id > 0) sold_products,
        (SELECT uniqExact(product_id) FROM inventory_snapshot FINAL WHERE product_id > 0) stocked_products
    """)
    if not rows:
        stats = coverage[0] if coverage else {}
        return [
            {"indicador": "ClickHouse", "valor": "Sin cargas", "estado": "Ejecuta el DAG globtrade_strategic_etl"},
            {"indicador": "Ventas publicadas", "valor": int(stats.get("sales_rows") or 0), "estado": "Pendiente"},
            {"indicador": "Inventario publicado", "valor": int(stats.get("inventory_rows") or 0), "estado": "Pendiente"},
        ][:limit]
    run = rows[0]
    stats = coverage[0] if coverage else {}
    return [
        {"indicador": "Última carga", "valor": str(run["loaded_at"]), "estado": str(run["status"]).upper()},
        {"indicador": "Ventas", "valor": int(run["rows_sales"]), "estado": "OK" if run["rows_sales"] else "Vacío"},
        {"indicador": "Compras", "valor": int(run["rows_purchases"]), "estado": "OK"},
        {"indicador": "Inventario", "valor": int(run["rows_inventory"]), "estado": "OK"},
        {"indicador": "Logística", "valor": int(run["rows_logistics"]), "estado": "OK"},
        {"indicador": "Cobertura ventas ↔ inventario", "valor": f"{int(stats.get('sold_products') or 0)} / {int(stats.get('stocked_products') or 0)} productos", "estado": "OK" if stats.get("sold_products") else "Sin producto"},
    ][:limit]


def rc09(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    purchase_date = ""
    if filters.get("start"):
        params["start"] = date.fromisoformat(str(filters["start"])[:10]); purchase_date += " AND purchase_date >= {start:Date}"
    if filters.get("end"):
        params["end"] = date.fromisoformat(str(filters["end"])[:10]); purchase_date += " AND purchase_date <= {end:Date}"
    return query_rows(f"""
      WITH sales AS (
        SELECT if(vendor='', 'Sin proveedor', vendor) proveedor, round(sum(profit),2) utilidad
        FROM fact_sales GROUP BY proveedor
      ), base AS (
        SELECT vendor proveedor, round(sum(amount),2) compras, uniqExact(purchase_id) ordenes
        FROM fact_purchases
        WHERE lowerUTF8(status) IN ('recibida','recibido','received','parcial','enviada','sent') {purchase_date}
        GROUP BY proveedor
      ), total AS (SELECT sum(compras) total_compras FROM base)
      SELECT base.proveedor proveedor, compras, ordenes, round(ifNull(any(sales.utilidad),0),2) utilidad,
             round(if(total_compras>0, compras/total_compras*100, 0), 2) participacion_pct,
             round(if(ordenes>0, compras/ordenes, 0), 2) ticket_promedio
      FROM base CROSS JOIN total LEFT JOIN sales ON base.proveedor=sales.proveedor
      GROUP BY proveedor, compras, ordenes, total_compras
      ORDER BY compras DESC LIMIT {{limit:UInt32}}
    """, params)


def rc10(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    rows = rc09(limit=limit, filters=filters)
    result = []
    for row in rows:
        pct = float(row.get("participacion_pct") or 0)
        riesgo = "Alto" if pct >= 45 else "Medio" if pct >= 25 else "Controlado"
        decision = (
            "Negociar respaldo o proveedor alterno."
            if riesgo == "Alto"
            else "Mantener seguimiento y comparar condiciones."
            if riesgo == "Medio"
            else "Dependencia saludable."
        )
        result.append({**row, "riesgo": riesgo, "decision": decision})
    return result


def rc11(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters, "fs")
    params["limit"] = limit
    return query_rows("""
      WITH purchases AS (
        SELECT vendor proveedor, round(sum(amount),2) compras
        FROM fact_purchases
        WHERE lowerUTF8(status) IN ('recibida','recibido','received','parcial','enviada','sent')
        GROUP BY proveedor
      )
      SELECT if(fs.vendor='', 'Sin proveedor', fs.vendor) proveedor,
             uniqExact(fs.order_id) pedidos, round(sum(fs.units),2) unidades,
             ifNull(any(purchases.compras),0) compras,
             round(sum(fs.revenue),2) ingresos, round(sum(fs.cost),2) costos, round(sum(fs.profit),2) utilidad,
             round(if(sum(fs.revenue)>0,sum(fs.profit)/sum(fs.revenue)*100,0),2) margen_pct
      FROM fact_sales fs LEFT JOIN purchases ON if(fs.vendor='', 'Sin proveedor', fs.vendor)=purchases.proveedor
      WHERE 1 /*filters*/
      GROUP BY proveedor
      HAVING ingresos > 0
      ORDER BY utilidad DESC, ingresos DESC
      LIMIT {limit:UInt32}
      SETTINGS prefer_column_name_to_alias = 1
    """.replace("/*filters*/", where), params)


def rc12(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    sales_date = purchase_date = ""
    if filters.get("start"):
        params["start"] = date.fromisoformat(str(filters["start"])[:10])
        sales_date += " AND sale_date >= {start:Date}"
        purchase_date += " AND purchase_date >= {start:Date}"
    if filters.get("end"):
        params["end"] = date.fromisoformat(str(filters["end"])[:10])
        sales_date += " AND sale_date <= {end:Date}"
        purchase_date += " AND purchase_date <= {end:Date}"
    for key in ("category", "region", "channel"):
        if filters.get(key):
            sales_date += f" AND {key} = {{{key}:String}}"
            params[key] = str(filters[key])
    rows = query_rows(f"""
      WITH s AS (
        SELECT if(vendor='', 'Sin proveedor', vendor) proveedor,
               round(sum(revenue),2) ingresos, round(sum(profit),2) utilidad
        FROM fact_sales WHERE 1 {sales_date} GROUP BY proveedor
      ), p AS (
        SELECT vendor proveedor, round(sum(amount),2) compras
        FROM fact_purchases
        WHERE lowerUTF8(status) IN ('recibida','recibido','received','parcial','enviada','sent') {purchase_date}
        GROUP BY proveedor
      ), names AS (
        SELECT proveedor FROM s UNION DISTINCT SELECT proveedor FROM p
      )
      SELECT names.proveedor proveedor, round(ifNull(p.compras,0),2) compras,
             round(ifNull(s.ingresos,0),2) ingresos, round(ifNull(s.utilidad,0),2) utilidad,
             round(if(ifNull(p.compras,0)>0, ifNull(s.utilidad,0)/p.compras*100, 0),2) retorno_pct
      FROM names LEFT JOIN s ON names.proveedor=s.proveedor LEFT JOIN p ON names.proveedor=p.proveedor
      ORDER BY utilidad DESC, ingresos DESC, compras DESC
      LIMIT {{limit:UInt32}}
    """, params)
    result = []
    for row in rows:
        retorno = float(row.get("retorno_pct") or 0)
        utilidad = float(row.get("utilidad") or 0)
        compras = float(row.get("compras") or 0)
        if utilidad <= 0 and compras > 0:
            decision = "Renegociar costo, revisar surtido o pausar compra."
        elif retorno >= 40:
            decision = "Proveedor estratégico: asegurar stock y mejores condiciones."
        elif retorno >= 15:
            decision = "Mantener y comparar precios con proveedores alternos."
        elif compras == 0 and utilidad > 0:
            decision = "Ventas con proveedor no registrado en compras; revisar trazabilidad."
        else:
            decision = "Seguimiento: utilidad baja frente a inversión."
        result.append({**row, "decision": decision})
    return result


def rc13(*, limit: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
    where, params = _filters(filters, "fs")
    params["limit"] = limit
    rows = query_rows("""
      WITH inv AS (
        SELECT product_id, round(sum(stock),2) stock_actual
        FROM inventory_snapshot FINAL GROUP BY product_id
      )
      SELECT if(fs.vendor='', 'Sin proveedor', fs.vendor) proveedor, fs.product producto, fs.category categoria,
             ifNull(any(inv.stock_actual),0) stock_actual,
             round(sum(fs.revenue),2) ingresos, round(sum(fs.profit),2) utilidad,
             round(if(sum(fs.revenue)>0,sum(fs.profit)/sum(fs.revenue)*100,0),2) margen_pct
      FROM fact_sales fs LEFT JOIN inv ON fs.product_id=inv.product_id
      WHERE fs.product_id > 0 /*filters*/
      GROUP BY proveedor, producto, categoria
      HAVING ingresos > 0
      ORDER BY utilidad DESC, margen_pct DESC
      LIMIT {limit:UInt32}
      SETTINGS prefer_column_name_to_alias = 1
    """.replace("/*filters*/", where), params)
    result = []
    for row in rows:
        margen = float(row.get("margen_pct") or 0)
        utilidad = float(row.get("utilidad") or 0)
        if utilidad <= 0:
            decision = "No reponer sin revisar costo/precio."
        elif margen >= 35:
            decision = "Impulsar y proteger inventario."
        elif margen >= 18:
            decision = "Mantener; buscar mejora de costo."
        else:
            decision = "Renegociar margen antes de escalar ventas."
        result.append({**row, "decision": decision})
    return result


_RUNNERS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "RC-01": rc01, "RC-02": rc02, "RC-03": rc03, "RC-04": rc04, "RC-05": rc05,
    "RC-06": rc06, "RC-07": rc07, "RC-08": rc08, "RC-09": rc09, "RC-10": rc10,
    "RC-11": rc11, "RC-12": rc12, "RC-13": rc13,
}


def run_complex_report(report_id: str, *, limit: int = 100, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    rid = (report_id or "").strip().upper()
    report = COMPLEX_BY_ID.get(rid)
    if not report:
        raise ValueError("unknown_report")
    if not ping_clickhouse():
        message = "ClickHouse no está disponible. Inicia el servicio y ejecuta el DAG globtrade_strategic_etl."
        rows = []
        if rid == "RC-08":
            rows = [
                {"indicador": "ClickHouse", "valor": "Sin conexión", "estado": "Detenido"},
                {"indicador": "Publicación de fact_ventas", "valor": "No verificable", "estado": "Pendiente"},
                {"indicador": "Acción requerida", "valor": "Ejecutar DAG", "estado": "globtrade_strategic_etl"},
            ]
        return {"report": _meta(report), "chart": report["chart"], "rows": rows, "total": len(rows), "message": message}
    ensure_database_and_schema()
    try:
        rows = _RUNNERS[rid](limit=max(1, min(int(limit), 2000)), filters=filters or {})
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_filters") from exc
    return {"report": _meta(report), "chart": report["chart"], "rows": rows, "total": len(rows), "filters": filters or {}}
