<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles: template placeholders -> project-specific GLOBTRADE principles
Added sections: Project Constraints; Development Workflow
Removed sections: none
Templates requiring updates: plan-template.md checked; spec-template.md checked; tasks-template.md checked
Follow-up TODOs: none
-->

# GLOBTRADE S.A. Constitution

## Core Principles

### I. Single Project Root
All implementation MUST live under `C:\proyect6softwa`. The `C:\vicuna` project is
only allowed as an operational dependency for the shared MongoDB container and
data-copy scripts explicitly documented in `README.md`. New code MUST NOT be added
to a second application repository.

### II. Package-First Quadrants
Each business quadrant MUST be implemented as a package under `paquetes/` with a
clear Flask blueprint boundary. Q1 uses `paquetes/tablero`, Q2 uses
`paquetes/analisis`, Q3 uses `paquetes/ventas`, Q4 uses `paquetes/datos`, and
access/session behavior uses `paquetes/acceso`. Shared database and configuration
logic belongs in `backend/shared` or `backend/config`, not duplicated per package.

### III. Visitor Read, Protected Write
Visitors MUST be able to navigate and read dashboard, analysis, sales, and data
views without an account. Sensitive actions MUST require an authenticated session
and the appropriate role before execution: generation, export, ELT/model build,
sales CRUD, and data modification. UI and code MUST avoid legacy or unrelated
branding terms that are not part of GLOBTRADE.

### IV. Data And Port Consistency
The application MUST use MongoDB database `globtrade_dw` through `MONGO_URI` and
the shared `globtrade-mongo` container on port 27017. The web app MUST run on host
port 5001 and the API surface on host port 8001 when applicable. Filters and KPIs
MUST account for the historical 2010-2017 dataset, including a "Todo el historico"
option so old data is not hidden by current-date defaults.

### V. Spanish User Experience
User-facing UI, messages, documentation for operation, and labels MUST be in
Spanish. The visual style SHOULD remain consistent with the Odoo-inspired layout:
four main navigation blocks, purple top bar `#714B67`, and coherent KPI/card
presentation across quadrants.

## Project Constraints

The platform is a Python/Flask web application with a single-page frontend in
`frontend/static/index.html`, MongoDB-backed data access, and Docker support. New
features SHOULD reuse existing query helpers and blueprints before introducing new
abstractions. Documentation MUST preserve traceability to the existing Kiro spec in
`.kiro/specs/globtrade-plataforma/` and the case-use documentation in
`C:\documentacion\`.

## Development Workflow

Work MUST proceed by independently testable increments: Q1 Tablero, Q3 Ventas, Q2
Analisis, Q4 Datos, then Acceso when a shared permission layer is needed across
write actions. Each increment MUST include a manual validation path in the browser
or API, exact file paths in tasks, and updates to README or Docker notes when
commands change. Before implementation is considered complete, run the relevant
startup or validation command and document any environment dependency that blocked
verification.

## Governance

This constitution supersedes ad hoc instructions when planning Spec Kit work.
Amendments require updating this file, checking `.specify/templates/plan-template.md`,
`.specify/templates/spec-template.md`, and `.specify/templates/tasks-template.md`
for consistency, and recording the semantic version change in the Sync Impact
Report. MAJOR changes redefine project boundaries or security principles, MINOR
changes add or materially expand principles, and PATCH changes clarify existing
rules. Every plan and task list MUST include a Constitution Check before coding.

**Version**: 1.0.0 | **Ratified**: 2026-06-21 | **Last Amended**: 2026-06-21
