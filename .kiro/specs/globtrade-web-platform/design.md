# Diseño — Plataforma web

## Stack

- Flask + CORS
- `frontend/mongo_manager.py` — agregaciones PyMongo sobre `sales_records`
- `frontend/static/` — HTML/JS del dashboard

## Rutas API (Flask)

| Ruta | Descripción |
|------|-------------|
| GET /api/summary | KPIs globales |
| GET /api/regions, /products, /trend | Gráficos |
| GET /api/orders | Búsqueda paginada |
| GET /api/elt_status | Parquet + nombre BD |

## Ejecución

```powershell
cd C:\vicuna
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
python frontend\app.py
```

Docker: servicio `web` en `docker-compose.yml`.
