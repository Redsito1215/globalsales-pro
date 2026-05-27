# Arquitectura por paquetes (áreas)

## Principio (diagrama RRHH → Sel Per → `.py`)

Cada **área funcional** es un **paquete** con:

- Casos de uso propios (CU-XX)
- Pantallas web y rutas Flask
- Módulos Python con una responsabilidad cada uno
- Dependencia común: MongoDB `globtrade_dw` vía capa compartida

## Paquetes del sistema

```text
GLOBTRADE/
├── paquetes/
│   ├── acceso/          # CU-01…08  — Steam, roles
│   ├── tablero/         # CU-09…14  — Q1 Dashboard
│   ├── analisis/        # CU-15…19  — Q2 Informes
│   ├── ventas/          # CU-20…25  — Q3 Pedidos
│   └── datos/           # CU-26…33  — Q4 Maestras, ELT, modelo
├── shared/              # mongo_manager, utilidades (o frontend/mongo_manager hasta migrar)
├── backend/etl/         # Pipeline archivo → Mongo (invocado desde paquete datos)
└── backend/api/         # FastAPI :8000 (CRUD desde CU-33)
```

## Estado actual vs objetivo

| Paquete | Hoy en `vicuna` | Objetivo |
|---------|-----------------|----------|
| acceso | No implementado | `paquetes/acceso/auth.py`, `sesion.py` |
| tablero | `frontend/app.py` + `mongo_manager` mezclado | Extraer rutas Q1 a `paquetes/tablero/` |
| analisis | Rutas en `app.py` | `paquetes/analisis/*.py` |
| ventas | `/api/orders` en `app.py` | `paquetes/ventas/*.py` |
| datos | `/master`, `build_model` | `paquetes/datos/*.py` |

**Migración gradual:** `frontend/app.py` registra blueprints por paquete; no reescribir todo de una vez.

## Documentación por paquete

`C:\documentacion\paquetes\<pkg_*>/README.md` — lista CU y archivos previstos.

Word único: `GLOBTRADE_Casos_de_Uso_Completos.docx` (secciones = paquetes).

## Trazabilidad

| Paquete | Requisitos | Tareas Kiro (fase) |
|---------|------------|-------------------|
| acceso | 5.x | Fase 5 |
| tablero | 1.x | Fase 1 |
| analisis | 2.x | Fase 3 |
| ventas | 3.x | Fase 2 |
| datos | 4.x, 7.x | Fase 4 |
