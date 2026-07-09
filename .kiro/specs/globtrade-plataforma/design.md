# Diseño — GLOBTRADE S.A.

## Raíz del código

**Única:** `C:\proyect6softwa`  
**MongoDB:** `globtrade_dw` en `localhost:27017` (contenedor `globtrade-mongo`).

## Estructura

```text
proyect6softwa/
├── paquetes/
│   ├── tablero/      Q1  CU-09…14
│   ├── analisis/     Q2  CU-15…19
│   ├── ventas/       Q3  CU-20…25
│   ├── datos/        Q4  CU-26…33
│   └── acceso/       CU-01…08
├── backend/shared/mongo.py
├── backend/etl/
├── frontend/app.py
└── docker-compose.yml
```

Detalle por paquete: **`paquetes.md`**

## UI — cuatro cuadrantes (25 % c/u)

| Q | Menú | Pantalla / API |
|---|------|----------------|
| Q1 | Inicio | Dashboard · `/api/summary`, gráficos, tabla |
| Q2 | Informes | Tendencias, Regiones, Productos |
| Q3 | Ventas | Explorar pedidos · `/api/orders` |
| Q4 | Datos | Maestras `/master`, modelo BD, cargar ELT |

Web **:5001** (host). Barra superior Odoo `#714B67`. Idioma español.

## Acceso

Visitante: GET y navegación. POST sensibles (generar, ELT, CRUD, exportar): sesión + rol en `paquetes/acceso/`.

## Docker

| Servicio | Puerto |
|----------|--------|
| `globtrade-saas-web` | 5001 |
| `globtrade-saas-api` | 8001 |
| `globtrade-mongo` | 27017 |

## API Flask (prefijo `/api`)

### Q1 — `paquetes/tablero`

GET `/health`, `/summary`, `/regions`, `/products`, `/trend`, `/channels`, `/priorities`, `/countries`, `/orders`, `/orders/count`  
POST `/sales_records/generate`  
GET `/elt_status`  

Query comunes: `region`, `item_type`, `channel`, `priority`, `months` (999 = todo el histórico; datos 2010–2017).

### Q3 — `paquetes/ventas`

GET `/orders`, `/orders/<order_id>` · POST/PUT/DELETE pedidos (admin).

### Q2 — `paquetes/analisis`

Reutiliza consultas de tablero; pantallas `page-trends`, `page-regions`, `page-products`.

### Q4 — `paquetes/datos`

GET `/master/tables`, `/master/<name>` · POST `/build_model` · GET `/elt_status` · POST `/load_dataset`  
HTML: GET `/master` → `master_tables.html` · `page-schema`, `page-load`

### Acceso — `paquetes/acceso`

POST `/auth/login`, `/auth/logout` · GET `/me`

## Frontend

Una `index.html` SPA: `showPage(id)` activa `page-dashboard`, `page-orders`, etc.
