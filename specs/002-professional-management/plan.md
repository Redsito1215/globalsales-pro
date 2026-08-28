# Implementation Plan: Gestión Profesional en 11 Fases

**Branch**: `working tree` | **Date**: 2026-08-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-professional-management/spec.md`

## Summary

Crear una consola profesional integrada con once fases para inicio por rol, alertas, fichas 360, proveedores, metas, aprobaciones, historial, calidad, búsqueda y consistencia visual. Se añade un paquete Flask que proyecta colecciones actuales, dos colecciones operativas pequeñas para metas y aprobaciones, y una página única con pestañas reutilizables.

## Technical Context

**Language/Version**: Python 3.11+ y JavaScript ES2020

**Primary Dependencies**: Flask, PyMongo y frontend HTML/CSS/JavaScript existente

**Storage**: MongoDB operativo/DW y ClickHouse analítico con degradación a MongoDB

**Testing**: pytest, cliente de pruebas Flask y pruebas unitarias de servicios

**Target Platform**: Aplicación web local/contenedores, navegadores modernos

**Project Type**: Aplicación web monolítica modular

**Performance Goals**: Respuestas de consulta comunes por debajo de 2 s y resultados limitados

**Constraints**: Reutilizar fuentes actuales, español, marca Altavia Trade, no añadir seguridad empresarial

**Scale/Scope**: 11 fases en una consola, 12 endpoints y 2 colecciones nuevas

## Constitution Check

- **Raíz única**: PASS; todo vive bajo `C:\proyect6softwa`.
- **Paquetes primero**: PASS; se usa `paquetes/profesional` y utilidades compartidas existentes.
- **Lectura/escritura protegida**: PASS; se conserva sesión y permisos existentes sin ampliar seguridad.
- **Datos y puertos**: PASS; se reutilizan MongoDB/ClickHouse y configuración actual.
- **Experiencia española**: PASS; textos en español y marca Altavia Trade. La paleta actual reemplaza el púrpura heredado por la identidad ya aprobada.

Revisión posterior al diseño: PASS sin excepciones.

## Project Structure

### Documentation (this feature)

```text
specs/002-professional-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/openapi.yaml
└── tasks.md
```

### Source Code (repository root)

```text
paquetes/profesional/
├── __init__.py
├── routes.py
└── services.py

frontend/static/
├── index.html
├── css/profesional.css
└── js/profesional.js

tests/
└── test_professional_center.py
```

**Structure Decision**: Paquete Flask de frontera propia, UI de una página con once pestañas y pruebas enfocadas en cálculos y contratos.

## Complexity Tracking

No existen violaciones que requieran justificación.
