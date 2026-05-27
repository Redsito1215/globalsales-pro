# Implementation Plan — GLOBTRADE plataforma (Odoo UI + Steam)

> Revisa y marca tareas cuando apruebes los casos de uso en `C:\documentacion`.
> Cada tarea referencia requisitos de `requirements.md`.

---

## Fase 0 — Alineación (antes de codificar)

- [ ] Revisar `GLOBTRADE_Casos_Uso_Acceso_Steam.docx` y validar contra requisitos **5.x**
- [ ] Revisar casos de uso en `Sistema_GLOBTRADE_Estilo_Odoo_Casos_de_Uso.docx` y mapear a **1.x–7.x**
- [ ] Confirmar con docente/cliente: roles (visitante / analista / admin)
- [ ] Aprobar esta spec en Kiro (Requirements → Design → **Task List**)

---

## Fase 1 — Q1 Tablero (25%) · Requirements: 1.x

- [ ] Verificar KPIs y gráficos con 200k registros en Docker (`7.1`, `7.3`)
  - [ ] Probar `/api/summary` y tiempo de respuesta aceptable
  - [ ] Ajustar límites de agregación si hay lentitud
- [ ] Consolidar filtros del dashboard (`1.2`)
  - [ ] Región, producto, canal, prioridad, meses aplican sin error
- [ ] Tabla paginada en dashboard (`1.4`)
- [ ] Documentar en informe qué ve el visitante en Q1 (`1.5`)

---

## Fase 2 — Q3 Pedidos (25%) · Requirements: 3.x

- [ ] Listado pedidos estable con paginación (`3.1`, `3.2`, `3.3`)
  - [ ] Filtros país / producto / canal / prioridad
  - [ ] Contador total coherente con MongoDB
- [ ] Vista detalle de pedido (`3.4`)
  - [ ] GET `/api/orders/<id>` enlazado desde la tabla
- [ ] Preparar hooks UI para CRUD (`3.5`) — botones visibles solo con rol admin (fase 4)

---

## Fase 3 — Q2 Análisis (25%) · Requirements: 2.x

- [ ] Pantalla Tendencias operativa (`2.1`)
- [ ] Pantalla Regiones y países (`2.2`)
- [ ] Pantalla Productos (`2.3`)
- [ ] Marcar botón Exportar como restringido hasta Fase 5 (`2.5`)

---

## Fase 4 — Q4 Datos / Maestras (25%) · Requirements: 4.x

- [ ] Vista Tablas maestras con 10 colecciones (`4.1`, `4.2`, `4.3`)
  - [ ] `/api/master/tables` y `/api/master/<name>`
- [ ] Botón Construir modelo protegido (`4.4`) — placeholder hasta auth
- [ ] Páginas Modelo BD y Cargar dataset (`4.5`, `4.6`)
- [ ] Indicador estado MongoDB en sidebar (`4.7`)

---

## Fase 5 — Acceso estilo Steam · Requirements: 5.x

- [ ] Modelo `users` en MongoDB y script seed admin (`5.3`, `5.5`)
- [ ] Rutas login / logout / `GET /api/me` (`5.3`, `5.4`)
- [ ] Middleware o decorador `@require_role` en rutas sensibles (`5.2`)
  - [ ] POST `/api/build_model`
  - [ ] POST generar ventas (cuando exista endpoint)
  - [ ] Exportar reportes
  - [ ] CRUD pedidos (cuando exista)
- [ ] Modal «Inicia sesión para continuar» en frontend (`5.1`, `5.2`)
- [ ] Pruebas: visitante no puede generar ni construir maestras

---

## Fase 6 — Skin Odoo · Requirements: 6.x

- [ ] Crear `frontend/static/css/odoo-theme.css` (`6.1`)
- [ ] Barra superior morada + botón Iniciar sesión (`6.1`, `6.2`)
- [ ] Reorganizar menú lateral en 4 secciones Q1–Q4 (`6.2`)
- [ ] Verificar que no cambia `MONGO_URI` / colecciones (`6.3`, `7.1`)

---

## Fase 7 — Cierre y entrega

- [ ] Actualizar README / capturas para informe escolar
- [ ] Checklist NFR (`NFR-1` … `NFR-4`)
- [ ] Demo: visitante explora → login → admin genera/exporta

---

## Notas

- No crear proyecto en `C:\globtrade-odoo` ni volver a `C:\globtrade`.
- ELT pesado sigue en `docker compose --profile etl-mongo` (spec `globtrade-mongodb`).
- Cuando digas **«procedemos»**, empezar por la fase que indiques (recomendado: **Fase 0** luego **Fase 5** o **Fase 6** según prioridad).
