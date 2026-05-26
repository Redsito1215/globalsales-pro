# Diseño — MongoDB / ELT

## Arquitectura

```text
CSV (data/sales.csv)
    → etl/csv_to_parquet.py → data/parquet/*.parquet
    → etl/load_parquet_to_mongo.py → MongoDB sales_records
    → etl/transform_fact_dimensions.py → fact_ventas, dim_*
```

## Servicios Docker

| Servicio   | Rol                          |
|-----------|------------------------------|
| mongo     | Base de datos                |
| api       | FastAPI CRUD                 |
| web       | Dashboard Flask (frontend/)  |
| etl-mongo | Pipeline sin PocketBase      |

## Carpetas

- `backend/etl/` — pipeline
- `backend/api/` — REST
- `backend/config/` — settings y auth PocketBase (opcional)
- `data/` — CSV, raw, parquet
- `db/schema.sql` — modelo relacional de referencia

## Conexión

- Docker: `mongodb://mongo:27017`
- Local: `mongodb://localhost:27017`
