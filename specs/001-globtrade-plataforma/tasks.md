# Tasks: Plataforma Web GLOBTRADE

**Input**: Design documents from `specs/001-globtrade-plataforma/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`

**Tests**: No se exige TDD completo; cada historia incluye validacion manual independiente en navegador/API.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Status (2026-08-13)**: Checklist cerrado + extensiones: tienda B2B, split Mongo ops/DW, asistente IA informes, perfil empresa. Fuera de alcance: SMTP real, pasarela de pago.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Consolidar la base Spec Kit y evitar filtracion de archivos privados.

- [x] T001 Verify `.cursor/` remains ignored in `.gitignore`
- [x] T002 [P] Review `README.md` quickstart commands against `specs/001-globtrade-plataforma/quickstart.md`
- [x] T003 [P] Confirm `docker-compose.yml` exposes web on 5001 and API on 8001
- [x] T004 Confirm Mongo dependency path `C:\vicuna` is documented only as container/data dependency

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar infraestructura compartida antes de ampliar cuadrantes.

**CRITICAL**: No user story work should start until this phase is complete.

- [x] T005 Verify `frontend/app.py` registers `auth_bp` and `tablero_bp`
- [x] T006 [P] Verify `backend/auth/decorators.py` exposes `login_required` and `admin_required`
- [x] T007 [P] Verify `backend/shared/mongo.py` centralizes Mongo access for `globtrade_dw`
- [x] T008 Add missing shared helper for sales order lookup/update/delete in `paquetes/tablero/queries.py` or new package-local query modules
- [x] T009 Confirm all user-facing labels added by new work are Spanish in `frontend/static/index.html`

**Checkpoint**: Foundation ready for story implementation.

---

## Phase 3: User Story 1 - Explorar tablero Q1 (Priority: P1) MVP

**Goal**: Preserve the existing Q1 dashboard and verify it remains demo-ready.

**Independent Test**: Open the app, select "Todo el historico", and verify KPIs, charts, and table populate.

### Implementation for User Story 1

- [x] T010 [US1] Validate Q1 summary, chart, and table endpoints in `paquetes/tablero/routes.py`
- [x] T011 [US1] Confirm historical period behavior uses `months=999` in `paquetes/tablero/queries.py`
- [x] T012 [US1] Confirm the dashboard period option "Todo el historico" exists in `frontend/static/index.html`
- [x] T013 [US1] Run the Q1 manual validation scenario from `specs/001-globtrade-plataforma/quickstart.md`
- [x] T014 [US1] Document any Q1 validation gap in `README.md`

**Checkpoint**: Q1 remains functional and independently demonstrable.

---

## Phase 4: User Story 2 - Explorar y administrar ventas Q3 (Priority: P2)

**Goal**: Add a Ventas package with order list, count, detail, and protected CRUD.

**Independent Test**: Open Ventas, filter/paginate orders, open detail, and verify write actions require administrator permissions.

### Implementation for User Story 2

- [x] T015 [P] [US2] Create `paquetes/ventas/__init__.py` exporting `ventas_bp`
- [x] T016 [P] [US2] Create read helpers `list_orders`, `count_orders`, and `get_order` in `paquetes/ventas/queries.py`
- [x] T017 [US2] Add create/update/delete helpers with validation in `paquetes/ventas/queries.py`
- [x] T018 [US2] Create `paquetes/ventas/routes.py` with GET `/api/sales/orders`, GET `/api/sales/orders/<order_id>`, POST, PUT, and DELETE routes
- [x] T019 [US2] Protect POST/PUT/DELETE sales routes with `admin_required` in `paquetes/ventas/routes.py`
- [x] T020 [US2] Register `ventas_bp` in `frontend/app.py`
- [x] T021 [US2] Add Ventas navigation and `page-orders` layout in `frontend/static/index.html`
- [x] T022 [US2] Add order filters and pagination behavior in `frontend/static/index.html`
- [x] T023 [US2] Add login-required/admin-required UI messages for create/edit/delete in `frontend/static/index.html`
- [x] T024 [US2] Run Q3 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q3 can be demonstrated without depending on Q2 or Q4.

---

## Phase 5: User Story 3 - Analizar tendencias Q2 (Priority: P3)

**Goal**: Add analysis views for trends, regions/countries, and products.

**Independent Test**: Open Informes, navigate the three analysis views, and confirm each respects filters and historical period.

### Implementation for User Story 3

- [x] T025 [P] [US3] Create `paquetes/analisis/__init__.py` exporting `analisis_bp`
- [x] T026 [P] [US3] Create `paquetes/analisis/routes.py` reusing tablero query datasets for trend, regions, and products
- [x] T027 [US3] Add authenticated export placeholder or endpoint in `paquetes/analisis/routes.py`
- [x] T028 [US3] Register `analisis_bp` in `frontend/app.py`
- [x] T029 [US3] Add Informes navigation entries in `frontend/static/index.html`
- [x] T030 [US3] Add `page-trends`, `page-regions`, and `page-products` views in `frontend/static/index.html`
- [x] T031 [US3] Wire analysis charts and empty states in `frontend/static/index.html`
- [x] T032 [US3] Run Q2 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q2 analysis is readable by visitors and export is protected.

---

## Phase 6: User Story 4 - Consultar y operar datos Q4 (Priority: P4)

**Goal**: Add Datos views for master tables, schema/model summary, Mongo status, and protected data operations.

**Independent Test**: Open Datos, browse a master table, inspect status/schema, and verify build/load actions require administrator permissions.

### Implementation for User Story 4

- [x] T033 [P] [US4] Create `paquetes/datos/__init__.py` exporting `datos_bp`
- [x] T034 [P] [US4] Create master table discovery and browse helpers in `paquetes/datos/maestras_queries.py`
- [x] T035 [US4] Create `paquetes/datos/routes.py` with GET `/api/master/tables`, GET `/api/master/<name>`, GET `/api/schema`, POST `/api/build_model`, and POST `/api/load_dataset`
- [x] T036 [US4] Protect build/load routes with `admin_required` in `paquetes/datos/routes.py`
- [x] T037 [US4] Register `datos_bp` in `frontend/app.py`
- [x] T038 [US4] Add Datos navigation and schema/load pages in `frontend/static/index.html`
- [x] T039 [US4] Create or update `frontend/static/master_tables.html` for master table browsing
- [x] T040 [US4] Run Q4 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q4 can read master data publicly and protect operations.

---

## Phase 7: User Story 5 - Acceso y roles (Priority: P5)

**Goal**: Complete cross-cutting access behavior for sensitive actions.

**Independent Test**: Register/login/logout, inspect `/api/auth/me`, and verify protected actions across Q1-Q4.

### Implementation for User Story 5

- [x] T041 [US5] Review `backend/auth/routes.py` for Spanish messages and role behavior
- [x] T042 [US5] Add analyst-role decorator if export actions need analyst-or-admin in `backend/auth/decorators.py`
- [x] T043 [US5] Ensure `frontend/static/index.html` exposes login, logout, and current-user state consistently
- [x] T044 [US5] Verify protected endpoints return clear 401/403 messages across Q1-Q4
- [x] T045 [US5] Run access validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Read access remains public and sensitive actions are protected.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Prepare demo and documentation.

- [x] T046 [P] Update `README.md` with completed Q2-Q4 and access status
- [x] T047 [P] Update `README-DOCKER.md` if Docker commands or exposed routes changed
- [x] T048 Run local startup validation from `specs/001-globtrade-plataforma/quickstart.md`
- [x] T049 Run Docker validation from `specs/001-globtrade-plataforma/quickstart.md`
- [x] T050 Record remaining academic/demo gaps in `.kiro/specs/globtrade-plataforma/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all stories.
- **US1 Q1 (Phase 3)**: Validate first because it is the current MVP.
- **US2 Q3 (Phase 4)**: Next implementation target; independent after foundation.
- **US3 Q2 (Phase 5)**: Can start after foundation, but benefits from Q1 query validation.
- **US4 Q4 (Phase 6)**: Can start after foundation, depends on Mongo/shared helpers.
- **US5 Access (Phase 7)**: Cross-cutting; can proceed alongside stories after foundation.
- **Polish**: Depends on desired stories being complete.

### User Story Dependencies

- **US1**: No dependency on other stories.
- **US2**: Depends on shared auth decorators and Mongo helpers.
- **US3**: Depends on Q1 query datasets.
- **US4**: Depends on Mongo helper and ETL/model modules.
- **US5**: Depends on auth base and protected endpoint list.

### Parallel Opportunities

- T002, T003, T006, T007 can run in parallel.
- Package file creation tasks for Q2/Q3/Q4 can run in parallel if different files are touched.
- UI tasks in `frontend/static/index.html` should be serialized to avoid merge conflicts.
- Documentation tasks T046 and T047 can run in parallel after implementation.

## Implementation Strategy

### MVP First

1. Complete setup and foundation.
2. Validate US1 Q1.
3. Implement US2 Q3.
4. Stop and demo Q1 + Q3 before adding Q2/Q4.

### Incremental Delivery

1. Q1 validated.
2. Q3 added and validated.
3. Q2 added and validated.
4. Q4 added and validated.
5. Access behavior verified across all write/export/load actions.

## Notes

- Use exact file paths in every implementation step.
- Mark each completed task as `[x]` in this file when implemented.
- Do not move code back to `C:\vicuna`; that project is only a Mongo/data dependency.
- Gaps demos restantes (no bloqueantes): pago/correo simulados a propósito; UI dual `/sem1` opcional; presentación oral.

---

## Extensión: ciclo de vida seguro de maestros (2026-08-24)

- [x] T051 [US4] Añadir pruebas de inhabilitación y bloqueo de borrado referencial en `tests/test_smoke.py`
- [x] T052 [US4] Incorporar estado `active` y referencias protegidas en `backend/shared/master_registry.py` y `paquetes/datos/services.py`
- [x] T053 [US4] Exponer cambio de estado protegido en `paquetes/datos/routes.py`
- [x] T054 [US4] Reemplazar eliminación normal por habilitar/inhabilitar y filtro de estado en `frontend/static/js/q4-datos.js` y `frontend/static/index.html`
- [x] T055 [US4] Preservar estado durante ELT y excluir maestros inactivos de nuevas operaciones en `backend/etl/transform_fact_dimensions.py`, `paquetes/shop/services.py` y `paquetes/ventas/services.py`

## Extensión: catálogos geográficos y operativos fijos (2026-08-24)

- [x] T056 [US4] Probar que Regiones, Países, Canales y Prioridades rechazan altas en `tests/test_smoke.py`
- [x] T057 [US4] Bloquear creación de catálogos fijos en API y ocultar `+ Nuevo` en Gestión

---

## Programa de fortalecimiento integral (sin movimientos entre bodegas)

### Fase A — Seguridad y consistencia

- [x] T058 Auditar capacidades existentes y excluir explícitamente movimientos entre bodegas
- [x] T059 Aplicar sesión inactiva configurable y cookies seguras en `frontend/app.py` y `backend/config/settings.py`
- [x] T060 Sustituir eliminación de proveedores por habilitar/inhabilitar con auditoría
- [x] T061 Exigir motivo en ajustes críticos de inventario y conservar trazabilidad
- [x] T062 Validar duplicados y relaciones en maestros, proveedores y catálogos operativos

### Fase B — Contabilidad

- [x] T063 Implementar conciliación pedido-pago-factura-caja y cuentas por cobrar
- [x] T064 Implementar cierres diarios/mensuales y bloqueo de períodos cerrados
- [x] T065 Implementar notas de crédito, anulaciones por contrapartida y consecutivos seguros
- [x] T066 Completar reportes de ingresos, costos, utilidad, impuestos y saldos

### Fase C — Inventario (sin transferencias entre bodegas)

- [x] T067 Implementar kardex inmutable por producto
- [x] T068 Separar disponible, comprometido, dañado y en tránsito
- [x] T069 Implementar mínimos, reposición, conteo físico y ajustes autorizados

### Fase D — Pedidos y pagos

- [x] T070 Registrar intentos de pago sin CVV ni PAN completo y bloquear duplicados
- [x] T071 Completar línea de tiempo, comprobantes y estados de pago/reembolso
- [x] T072 Integrar cancelaciones/devoluciones con inventario y contabilidad

### Fase E — Gestión comercial

- [x] T073 Implementar vigencia e historial de precios, costos y descuentos
- [x] T074 Implementar límites de compra, margen mínimo y autorización de excepción
- [x] T075 Implementar segmentación de clientes, crédito y destacados comerciales

### Fase F — Calidad y recuperación

- [x] T076 Automatizar respaldos verificables y consulta segura de respaldos
- [x] T077 Implementar salud integral y registro central de errores
- [x] T078 Completar pruebas por rol, dinero, inventario y concurrencia
- [x] T079 Ejecutar recorridos integrales y actualizar documentación final

**Exclusión confirmada**: no se implementarán movimientos ni transferencias entre bodegas.

## Programa de mejora posterior por fases

### Fase 1 — Panel visual de gestión comercial

- [x] T080 Añadir navegación y pantalla administrativa comercial en `frontend/static/index.html`
- [x] T081 Implementar gestión visual de políticas y descuentos en `frontend/static/js/commercial-admin.js`
- [x] T082 Implementar bandeja de excepciones y condiciones de crédito por cliente
- [x] T083 Implementar productos destacados e historial de precios/costos
- [x] T084 Aplicar diseño adaptable y validar regresión completa

### Fase 2 — Seguridad y control de concurrencia

- [x] T085 Implementar reserva atómica de existencias para evitar sobreventa
- [x] T086 Revertir todas las reservas si el checkout falla parcialmente
- [x] T087 Hacer seguro el limitador de intentos concurrentes y limitar por IP/cuenta
- [x] T088 Restringir CORS y exigir secretos seguros en configuración de producción
- [x] T089 Auditar permisos de escritura y agregar pruebas de seguridad/concurrencia

### Fase 3 — Pruebas comerciales de integración

- [x] T090 Probar límites mínimo/máximo, límite por cliente y margen mínimo
- [x] T091 Probar autorización, alcance y consumo único de excepciones comerciales
- [x] T092 Probar cupones vigentes, futuros, vencidos, por segmento y concurrencia de usos
- [x] T093 Probar crédito habilitado, deshabilitado y excedido
- [x] T094 Probar compra simultánea y reversión de reservas en recorrido comercial
- [x] T095 Corregir defectos encontrados, ejecutar regresión y documentar resultados

### Fase 4 — Contabilidad avanzada

- [x] T096 Implementar estado de cuenta consolidado por cliente
- [x] T097 Implementar antigüedad de cartera y vencimiento de crédito
- [x] T098 Implementar abonos parciales con saldo y trazabilidad
- [x] T099 Implementar análisis de margen por producto, cliente, canal y país
- [x] T100 Integrar controles en la pantalla de caja y validar regresión contable

### Fase 5 — Auditoría administrativa

- [x] T101 Registrar módulo y comparación anterior/nueva con protección de datos sensibles
- [x] T102 Filtrar auditoría por usuario, rol, módulo, acción y rango de fechas
- [x] T103 Mostrar el detalle de cambios de cada evento en la interfaz administrativa
- [x] T104 Exportar el resultado filtrado en CSV compatible con Excel
- [x] T105 Ejecutar pruebas específicas y regresión completa, y documentar resultados

### Fase 6 — Experiencia de usuario y accesibilidad

- [x] T106 Añadir salto al contenido, foco visible y anuncio de cambios de pantalla
- [x] T107 Normalizar semántica, foco inicial, retorno de foco y navegación cíclica en modales
- [x] T108 Vincular etiquetas de formulario y completar nombres accesibles de controles principales
- [x] T109 Respetar movimiento reducido, alto contraste y navegación adaptable
- [x] T110 Ejecutar validación de sintaxis, pruebas específicas y regresión completa

### Fase 7 — Documentación y preparación final

- [x] T111 Consolidar instalación, operación, roles, reglas críticas y recuperación
- [x] T112 Documentar límites de integración y exclusiones sin confundirlos con defectos funcionales
- [x] T113 Actualizar README, plan de pruebas y textos visibles desfasados
- [x] T114 Implementar verificación automática y no destructiva de preparación
- [x] T115 Ejecutar verificación final, regresión y cerrar documentación de entrega

### Fase 8 — Rendimiento del tablero con 2 millones de registros

- [x] T116 Eliminar el escaneo completo usado para calcular la fecha de anclaje
- [x] T117 Consolidar resumen y gráficos en una única agregación MongoDB
- [x] T118 Añadir un índice compuesto para los filtros combinados del tablero
- [x] T119 Reducir seis solicitudes del navegador a una respuesta consolidada
- [x] T120 Medir carga en frío/caliente y ejecutar la regresión automatizada

### Fase 9 — Airflow seguro para presentación

- [x] T121 Sustituir la carga destructiva desde CSV por inspección de la landing Mongo actual
- [x] T122 Preservar los 2 millones de registros y sincronizar únicamente pendientes
- [x] T123 Mantener validación estratégica e índices sin reconstrucción completa en memoria
- [x] T124 Ejecutar manualmente el DAG y verificar las cuatro tareas en verde
