# GLOBTRADE — Requisitos (MongoDB / Pozo)

## Objetivo

Almacenar el dataset de ventas y el modelo dimensional en **MongoDB** (`globtrade_dw`), con ELT desde CSV o PocketBase.

## Requisitos funcionales

1. **Colección principal** `sales_records` con métricas de ventas.
2. **Catálogos**: regions, countries, products, sales_channels, order_priorities, product_categories, orders, order_lines, monthly_kpis.
3. **Modelo analítico**: `fact_ventas`, dimensiones `dim_*` generadas por el ELT.
4. **Pipeline ELT** (perfil Docker `etl-mongo`): CSV → Parquet en `data/parquet/` → carga MongoDB → transformaciones.
5. **API CRUD** (FastAPI, puerto 8000) sobre hechos y dimensiones.
6. **Healthcheck** MongoDB en Docker Compose.

## Requisitos no funcionales

- MongoDB 7 en contenedor `globtrade-mongo` (puerto 27017).
- Variables en `.env`: `MONGO_URI`, `MONGO_DB`.
- Compatible con **Kiro** y desarrollo local con **Docker Desktop**.

## Fuera de alcance (no usar)

- **DuckDB** — no forma parte de este stack.
- **PostgreSQL en producción** — `db/schema.sql` es solo referencia documental.
