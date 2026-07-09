# Tasks: Plataforma Web GLOBTRADE

**Input**: Design documents from `specs/001-globtrade-plataforma/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`

**Tests**: No se exige TDD completo; cada historia incluye validacion manual independiente en navegador/API.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Consolidar la base Spec Kit y evitar filtracion de archivos privados.

- [ ] T001 Verify `.cursor/` remains ignored in `.gitignore`
- [ ] T002 [P] Review `README.md` quickstart commands against `specs/001-globtrade-plataforma/quickstart.md`
- [ ] T003 [P] Confirm `docker-compose.yml` exposes web on 5001 and API on 8001
- [ ] T004 Confirm Mongo dependency path `C:\vicuna` is documented only as container/data dependency

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirmar infraestructura compartida antes de ampliar cuadrantes.

**CRITICAL**: No user story work should start until this phase is complete.

- [ ] T005 Verify `frontend/app.py` registers `auth_bp` and `tablero_bp`
- [ ] T006 [P] Verify `backend/auth/decorators.py` exposes `login_required` and `admin_required`
- [ ] T007 [P] Verify `backend/shared/mongo.py` centralizes Mongo access for `globtrade_dw`
- [ ] T008 Add missing shared helper for sales order lookup/update/delete in `paquetes/tablero/queries.py` or new package-local query modules
- [ ] T009 Confirm all user-facing labels added by new work are Spanish in `frontend/static/index.html`

**Checkpoint**: Foundation ready for story implementation.

---

## Phase 3: User Story 1 - Explorar tablero Q1 (Priority: P1) MVP

**Goal**: Preserve the existing Q1 dashboard and verify it remains demo-ready.

**Independent Test**: Open the app, select "Todo el historico", and verify KPIs, charts, and table populate.

### Implementation for User Story 1

- [ ] T010 [US1] Validate Q1 summary, chart, and table endpoints in `paquetes/tablero/routes.py`
- [ ] T011 [US1] Confirm historical period behavior uses `months=999` in `paquetes/tablero/queries.py`
- [ ] T012 [US1] Confirm the dashboard period option "Todo el historico" exists in `frontend/static/index.html`
- [ ] T013 [US1] Run the Q1 manual validation scenario from `specs/001-globtrade-plataforma/quickstart.md`
- [ ] T014 [US1] Document any Q1 validation gap in `README.md`

**Checkpoint**: Q1 remains functional and independently demonstrable.

---

## Phase 4: User Story 2 - Explorar y administrar ventas Q3 (Priority: P2)

**Goal**: Add a Ventas package with order list, count, detail, and protected CRUD.

**Independent Test**: Open Ventas, filter/paginate orders, open detail, and verify write actions require administrator permissions.

### Implementation for User Story 2

- [ ] T015 [P] [US2] Create `paquetes/ventas/__init__.py` exporting `ventas_bp`
- [ ] T016 [P] [US2] Create read helpers `list_orders`, `count_orders`, and `get_order` in `paquetes/ventas/queries.py`
- [ ] T017 [US2] Add create/update/delete helpers with validation in `paquetes/ventas/queries.py`
- [ ] T018 [US2] Create `paquetes/ventas/routes.py` with GET `/api/sales/orders`, GET `/api/sales/orders/<order_id>`, POST, PUT, and DELETE routes
- [ ] T019 [US2] Protect POST/PUT/DELETE sales routes with `admin_required` in `paquetes/ventas/routes.py`
- [ ] T020 [US2] Register `ventas_bp` in `frontend/app.py`
- [ ] T021 [US2] Add Ventas navigation and `page-orders` layout in `frontend/static/index.html`
- [ ] T022 [US2] Add order filters and pagination behavior in `frontend/static/index.html`
- [ ] T023 [US2] Add login-required/admin-required UI messages for create/edit/delete in `frontend/static/index.html`
- [ ] T024 [US2] Run Q3 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q3 can be demonstrated without depending on Q2 or Q4.

---

## Phase 5: User Story 3 - Analizar tendencias Q2 (Priority: P3)

**Goal**: Add analysis views for trends, regions/countries, and products.

**Independent Test**: Open Informes, navigate the three analysis views, and confirm each respects filters and historical period.

### Implementation for User Story 3

- [ ] T025 [P] [US3] Create `paquetes/analisis/__init__.py` exporting `analisis_bp`
- [ ] T026 [P] [US3] Create `paquetes/analisis/routes.py` reusing tablero query datasets for trend, regions, and products
- [ ] T027 [US3] Add authenticated export placeholder or endpoint in `paquetes/analisis/routes.py`
- [ ] T028 [US3] Register `analisis_bp` in `frontend/app.py`
- [ ] T029 [US3] Add Informes navigation entries in `frontend/static/index.html`
- [ ] T030 [US3] Add `page-trends`, `page-regions`, and `page-products` views in `frontend/static/index.html`
- [ ] T031 [US3] Wire analysis charts and empty states in `frontend/static/index.html`
- [ ] T032 [US3] Run Q2 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q2 analysis is readable by visitors and export is protected.

---

## Phase 6: User Story 4 - Consultar y operar datos Q4 (Priority: P4)

**Goal**: Add Datos views for master tables, schema/model summary, Mongo status, and protected data operations.

**Independent Test**: Open Datos, browse a master table, inspect status/schema, and verify build/load actions require administrator permissions.

### Implementation for User Story 4

- [ ] T033 [P] [US4] Create `paquetes/datos/__init__.py` exporting `datos_bp`
- [ ] T034 [P] [US4] Create master table discovery and browse helpers in `paquetes/datos/maestras_queries.py`
- [ ] T035 [US4] Create `paquetes/datos/routes.py` with GET `/api/master/tables`, GET `/api/master/<name>`, GET `/api/schema`, POST `/api/build_model`, and POST `/api/load_dataset`
- [ ] T036 [US4] Protect build/load routes with `admin_required` in `paquetes/datos/routes.py`
- [ ] T037 [US4] Register `datos_bp` in `frontend/app.py`
- [ ] T038 [US4] Add Datos navigation and schema/load pages in `frontend/static/index.html`
- [ ] T039 [US4] Create or update `frontend/static/master_tables.html` for master table browsing
- [ ] T040 [US4] Run Q4 validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Q4 can read master data publicly and protect operations.

---

## Phase 7: User Story 5 - Acceso y roles (Priority: P5)

**Goal**: Complete cross-cutting access behavior for sensitive actions.

**Independent Test**: Register/login/logout, inspect `/api/auth/me`, and verify protected actions across Q1-Q4.

### Implementation for User Story 5

- [ ] T041 [US5] Review `backend/auth/routes.py` for Spanish messages and role behavior
- [ ] T042 [US5] Add analyst-role decorator if export actions need analyst-or-admin in `backend/auth/decorators.py`
- [ ] T043 [US5] Ensure `frontend/static/index.html` exposes login, logout, and current-user state consistently
- [ ] T044 [US5] Verify protected endpoints return clear 401/403 messages across Q1-Q4
- [ ] T045 [US5] Run access validation scenario from `specs/001-globtrade-plataforma/quickstart.md`

**Checkpoint**: Read access remains public and sensitive actions are protected.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Prepare demo and documentation.

- [ ] T046 [P] Update `README.md` with completed Q2-Q4 and access status
- [ ] T047 [P] Update `README-DOCKER.md` if Docker commands or exposed routes changed
- [ ] T048 Run local startup validation from `specs/001-globtrade-plataforma/quickstart.md`
- [ ] T049 Run Docker validation from `specs/001-globtrade-plataforma/quickstart.md`
- [ ] T050 Record remaining academic/demo gaps in `.kiro/specs/globtrade-plataforma/tasks.md`

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
