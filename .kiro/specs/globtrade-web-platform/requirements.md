# GLOBTRADE — Requisitos (plataforma web)

## Objetivo

Dashboard en **Flask** (`frontend/`) que consume MongoDB tras el ELT.

## Requisitos funcionales

1. Página principal con KPIs (`/api/summary`).
2. Gráficos: regiones, productos, tendencia, canales, prioridades, países.
3. Consulta de pedidos con filtros y paginación.
4. Estado del ELT (`/api/elt_status`) — existencia de Parquet.
5. Vista de tablas maestras (`static/master_tables.html`).

## Requisitos no funcionales

- Puerto 5000 (`WEB_PORT` en `.env`).
- Estáticos en `frontend/static/`.
- Desarrollo con **Kiro** apuntando a `frontend/app.py`.

## Dependencias

- MongoDB con datos cargados (ver spec `globtrade-mongodb`).
- `PYTHONPATH` incluye `backend/` (configurado en `.vscode/settings.json`).
