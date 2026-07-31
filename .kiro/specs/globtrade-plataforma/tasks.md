# Implementation Plan — GLOBTRADE S.A.

> **Kiro:** implementar en orden. Marcar `[x]` al terminar.  
> Referencia: `requirements.md` · `design.md` · `paquetes.md`

**Cierre demo (2026-07-29):** checklist Spec Kit en `specs/001-globtrade-plataforma/tasks.md` marcado completo.  
Gaps no bloqueantes: pago/correo simulados; UI legacy `/sem1` opcional; rúbrica oral.  
Fuente de verdad de tareas: Spec Kit (`specs/.../tasks.md`), no este archivo Kiro histórico.

---

## Fase 0 — Bootstrap (recrear proyecto vacío)

- [ ] Crear estructura: `frontend/`, `backend/config`, `backend/shared`, `backend/etl`, `backend/api`, `paquetes/`, `scripts/`, `data/`
- [ ] `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`
- [ ] Copiar ELT desde backup o regenerar `backend/etl/*` (csv_to_parquet, load_parquet, transform, run_pipeline_mongo)
- [ ] `data/sales.csv` + opcional parquet (`scripts\copiar_data_desde_vicuna.ps1` si existe backup)
- [ ] Mongo `globtrade-mongo` Up — **Dónde:** CMD `C:\vicuna` → `docker compose up -d mongo`

---

## Fase 1 — Q1 Tablero (25 %) · Req 1.x · Paquete `tablero`

- [x] `paquetes/tablero/queries.py` — summary, regions, products, trend, channels, orders
- [x] `paquetes/tablero/routes.py` — blueprint `/api/*`
- [x] `paquetes/tablero/generar_ventas.py` — POST `/api/sales_records/generate`
- [x] `frontend/app.py` — registrar blueprint
- [x] `frontend/static/index.html` — solo Q1, barra Odoo, período «Todo el histórico»
- [x] Docker `globtrade-saas-web` :5001 — `scripts\docker-up.cmd`
- [ ] GA: verificar **300 000** registros en `sales_records`
- [ ] Proteger generar ventas con login (tras Fase 5)

---

## Fase 2 — Q3 Ventas (25 %) · Req 3.x · Paquete `ventas`

- [ ] Crear `paquetes/ventas/__init__.py` exporta `ventas_bp`
- [ ] `paquetes/ventas/queries.py` — reutilizar search_orders, get_order, CRUD insert/update/delete
- [ ] `paquetes/ventas/routes.py` — GET list/count/detail, POST/PUT/DELETE (admin)
- [ ] Registrar `ventas_bp` en `frontend/app.py` (url_prefix `/api`)
- [ ] En `index.html`: sección `page-orders` con filtros país/producto/canal/prioridad, paginación 50/100/200
- [ ] Botones Nuevo/Editar/Eliminar visibles; deshabilitados o modal login hasta Fase 5
- [ ] Probar: **Dónde** navegador → menú Ventas → listado con datos

---

## Fase 3 — Q2 Análisis (25 %) · Req 2.x · Paquete `analisis`

- [ ] `paquetes/analisis/routes.py` — proxy o reexport GET trend, regions, products
- [ ] `index.html`: `page-trends`, `page-regions`, `page-products` (Chart.js)
- [ ] Menú lateral subsección «Informes» con 3 entradas
- [ ] Botón Exportar (alert o modal «requiere sesión» hasta Fase 5)
- [ ] Probar las 3 pantallas con «Todo el histórico»

---

## Fase 4 — Q4 Datos (25 %) · Req 4.x · Paquete `datos`

- [ ] `paquetes/datos/maestras_queries.py` — master_tables, master_browse (10 colecciones dim_*)
- [ ] `paquetes/datos/routes.py` — /api/master/*, POST /api/build_model, GET /api/elt_status
- [ ] `frontend/static/master_tables.html` — selector tabla + búsqueda + paginación
- [ ] `frontend/app.py` — ruta `GET /master`
- [ ] `index.html`: `page-schema` (grid tarjetas esquema), `page-load` (botón ELT + log)
- [ ] `build_model` llama `etl.transform_fact_dimensions.main`
- [ ] ELT: **Dónde** CMD `C:\proyect6softwa` → `docker compose --profile etl-mongo run --rm etl-mongo`

---

## Fase 5 — Acceso y sesión · Req 5.x · Paquete `acceso`

- [ ] `paquetes/acceso/auth.py` — hash password, validar usuario
- [ ] `paquetes/acceso/sesion.py` — decorador `@require_role("admin"|"analyst")`
- [ ] `paquetes/acceso/routes.py` — POST login/logout, GET me
- [ ] Colección MongoDB `users` + script `scripts/seed_admin.py` (admin@globtrade.local)
- [ ] `index.html`: modal login, botón barra «Iniciar sesión», menú cerrar sesión
- [ ] Proteger: generate, build_model, load_dataset, CRUD pedidos, exportar

---

## Fase 6 — Skin Odoo completo · Req 6.x

- [ ] `frontend/static/css/odoo-theme.css` — variables #714B67, layout
- [ ] Menú lateral: 4 bloques Q1 Inicio | Q2 Informes | Q3 Ventas | Q4 Datos
- [ ] Unificar tipografía y tarjetas KPI en las 4 áreas
- [ ] favicon opcional `/static/favicon.ico`

---

## Fase 7 — Cierre

- [ ] README, README-DOCKER, capturas GA03
- [ ] Demo video :5001 — tablero + roadmap Q2–Q4

