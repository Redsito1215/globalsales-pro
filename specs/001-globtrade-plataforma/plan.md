# Implementation Plan: Plataforma Web GLOBTRADE

**Branch**: `001-globtrade-plataforma` | **Date**: 2026-06-21 | **Spec**: `specs/001-globtrade-plataforma/spec.md`

**Input**: Feature specification from `specs/001-globtrade-plataforma/spec.md`

## Summary

Formalizar y completar la plataforma web GLOBTRADE como una aplicacion Flask con
cuatro cuadrantes: Q1 Tablero, Q2 Informes, Q3 Ventas y Q4 Datos. Q1 y la base de
autenticacion ya existen; el trabajo restante debe extender paquetes Flask,
registrar blueprints, ampliar la SPA estatica y proteger acciones sensibles.

## Technical Context

**Language/Version**: Python 3.12+; HTML/CSS/JavaScript en frontend estatico

**Primary Dependencies**: Flask, Flask-CORS, PyMongo, python-dotenv, pandas, pyarrow, FastAPI/Uvicorn para API auxiliar

**Storage**: MongoDB `globtrade_dw`, coleccion principal `sales_records`, coleccion de usuarios y colecciones maestras `dim_*`

**Testing**: Validacion manual en navegador/API; pruebas Python opcionales si se agrega cobertura enfocada

**Target Platform**: Windows 10/11 con PowerShell; Docker Desktop para despliegue local

**Project Type**: Web application monorepo

**Performance Goals**: Filtros y listados deben responder de forma usable para una demo academica con hasta 300 000 registros

**Constraints**: Web en puerto 5001, API en 8001, Mongo compartido en 27017, UI en espanol, codigo dentro de `C:\proyect6softwa`

**Scale/Scope**: Cuatro cuadrantes funcionales, un flujo de acceso, dataset historico 2010-2017, una demo local/Docker

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single Project Root**: PASS. Todos los archivos nuevos se planifican bajo `C:\proyect6softwa`.
- **Package-First Quadrants**: PASS. Q2, Q3, Q4 y acceso se organizan bajo `paquetes/`.
- **Visitor Read, Protected Write**: PASS. Lectura publica y acciones sensibles protegidas por sesion/rol.
- **Data And Port Consistency**: PASS. Se mantiene `globtrade_dw`, web 5001, API 8001 y Mongo 27017.
- **Spanish User Experience**: PASS. UI, mensajes y documentacion operativa se mantienen en espanol.

## Project Structure

### Documentation (this feature)

```text
specs/001-globtrade-plataforma/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── auth/                 # sesion, usuarios, decoradores existentes
├── config/               # settings
├── etl/                  # transformaciones y carga
└── shared/               # conexion Mongo compartida

frontend/
├── app.py                # app Flask y registro de blueprints
└── static/
    ├── index.html        # SPA principal
    └── css/              # tema visual

paquetes/
├── tablero/              # Q1 existente
├── analisis/             # Q2 pendiente
├── ventas/               # Q3 pendiente
├── datos/                # Q4 pendiente
└── acceso/               # capa de acceso si se decide mover auth desde backend/auth

scripts/
├── iniciar-web.cmd
├── iniciar-web.ps1
└── docker-up.cmd
```

**Structure Decision**: Mantener la arquitectura actual: una aplicacion Flask
principal con blueprints por paquete y una SPA estatica. `backend/auth` ya existe
y puede seguir siendo la fuente de autenticacion; `paquetes/acceso` se reserva
solo si se requiere fachada por paquete para cumplir trazabilidad academica.

## Complexity Tracking

No constitution violations identified.

## Phase 0: Research

See `research.md`.

## Phase 1: Design & Contracts

See `data-model.md`, `contracts/api.md`, and `quickstart.md`.

## Post-Design Constitution Check

- **Single Project Root**: PASS. Artefactos y tareas usan rutas relativas al repo.
- **Package-First Quadrants**: PASS. Las tareas separan `analisis`, `ventas` y `datos`.
- **Visitor Read, Protected Write**: PASS. Contratos distinguen GET publico y POST/PUT/DELETE protegido.
- **Data And Port Consistency**: PASS. Quickstart valida Mongo y puerto 5001.
- **Spanish User Experience**: PASS. Tareas incluyen labels y mensajes en espanol.
