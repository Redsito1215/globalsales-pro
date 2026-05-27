# Diseño — GLOBTRADE plataforma (Odoo UI + Steam + 4 cuadrantes)

## Contexto

Proyecto único: `C:\vicuna`. No se crean carpetas paralelas de código. La BD MongoDB existente (`globtrade_dw`) no se migra.

**Organización por paquetes (áreas):** cada cuadrante web + acceso Steam = un paquete con sus CU y módulos `.py`. Ver `paquetes.md` y `C:\documentacion\paquetes\`.

```text
┌─────────────────────────────────────────────────────────┐
│  Barra superior (estilo Odoo): logo · menú · Iniciar sesión │
├──────────────┬──────────────────────────────────────────────┤
│ Menú lateral │  Área de contenido (vista activa)           │
│              │                                              │
│ Q1 Inicio    │  KPIs · gráficos · tablas                    │
│ Q2 Informes  │  Tendencias / Regiones / Productos           │
│ Q3 Ventas    │  Lista pedidos · formulario (auth)           │
│ Q4 Datos     │  Maestras · Modelo · Cargar (auth)           │
└──────────────┴──────────────────────────────────────────────┘
         │                              │
         └──────── Flask :5000 ─────────┘
                        │
              mongo_data / mongo_manager
                        │
                 MongoDB globtrade_dw
```

## Mapa cuadrante → pantalla → API

| Cuadrante | Menú Odoo (objetivo) | Pantalla actual (`frontend/static`) | API principal |
|-----------|----------------------|-------------------------------------|---------------|
| Q1 25% | Inicio | `page-dashboard` | `/api/summary`, `/api/regions`, … |
| Q2 25% | Informes | `page-trends`, `page-regions`, `page-products` | `/api/trend`, `/api/regions`, `/api/products` |
| Q3 25% | Ventas › Pedidos | `page-orders` | `/api/orders`, `/api/orders/count` |
| Q4 25% | Catálogo / Ajustes | `/master`, `page-schema`, `page-load` | `/api/master/*`, `/api/build_model`, `/api/elt_status` |

## Acceso estilo Steam — diseño de comportamiento

```text
[Visitante] ──► Navega Q1–Q4 (GET, solo lectura)
      │
      ├─► Pulsa acción restringida
      │         │
      │         ▼
      │   ¿Sesión válida? ──No──► Modal «Inicia sesión»
      │         │
      │        Sí
      │         ▼
      │   ¿Rol permite? ──No──► 403 / mensaje permiso
      │         │
      │        Sí
      │         ▼
      │   Ejecutar (export / POST generate / CRUD / build_model)
```

### Matriz acción × autenticación

| Acción | Visitante | Analista | Admin |
|--------|-----------|----------|-------|
| Ver KPIs/gráficos | ✓ | ✓ | ✓ |
| Filtrar / paginar | ✓ | ✓ | ✓ |
| Exportar reporte | ✗ → login | ✓ | ✓ |
| Generar ventas | ✗ → login | ✗ | ✓ |
| CRUD pedidos | ✗ → login | ✗ | ✓ |
| Construir maestras / ELT | ✗ → login | ✗ | ✓ |

## Autenticación (fase a implementar)

- **Almacenamiento:** colección MongoDB `users` (email, hash contraseña, `role`: `analyst` | `admin`).
- **Sesión:** cookie firmada Flask (`session`) o JWT en header para API.
- **Decorador** `@require_auth` / `@require_role('admin')` en rutas POST sensibles.
- **Frontend:** flag `window.USER` o endpoint `GET /api/me`; deshabilitar botones si no hay permiso.

Rutas nuevas previstas:

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/login` | Formulario login |
| POST | `/api/auth/login` | Crear sesión |
| POST | `/api/auth/logout` | Cerrar sesión |
| GET | `/api/me` | Usuario y rol actual |

## UI Odoo — tokens visuales

| Elemento | Valor orientativo |
|----------|-------------------|
| Barra superior | `#714B67` (morado Odoo) |
| Acento / activo | `#00A09D` o verde corporativo GLOBTRADE |
| Fondo contenido | `#F0EEEE` |
| Tarjetas | blanco, borde `#DEE2E6` |
| Tipografía | Segoe UI / sistema |

Implementación: nuevo `frontend/static/css/odoo-theme.css` + refactor progresivo de `index.html` (no reemplazo big-bang obligatorio).

## Componentes backend (sin duplicar)

| Módulo | Responsabilidad |
|--------|-----------------|
| `frontend/mongo_manager.py` | Agregaciones y maestras (existente) |
| `frontend/app.py` | Rutas Flask + auth (extender) |
| `backend/api/main.py` | CRUD FastAPI dimensiones/hechos |
| `backend/etl/transform_fact_dimensions.py` | `build_model` |

## Docker

- Un solo `docker-compose.yml` en raíz `C:\vicuna`.
- Servicios: `mongo`, `web`, `api`.
- Variable `MONGO_URI=mongodb://mongo:27017` dentro de compose; `localhost:27017` en host.

## Trazabilidad documentación

| Documento | Contenido |
|-----------|-----------|
| `GLOBTRADE_4_Cuadrantes_Pagina_Web.docx` | Detalle Q1–Q4 por capacidad web |
| `GLOBTRADE_Casos_Uso_Acceso_Steam.docx` | CU-A01 … CU-A08 |
| `Sistema_GLOBTRADE_Estilo_Odoo_Casos_de_Uso.docx` | Casos de uso por módulo técnico (revisar vs 1.x–7.x) |

Al revisar casos de uso, cada CU debe citar requisito (ej. `Requirements: 5.2`).
