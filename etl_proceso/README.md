# ETL estratégico GLOBTRADE (`etl_proceso`)

Pipeline **Extract → Load → Transform → Validate** que alimenta la capa estratégica
(`sales_records` landing → `fact_ventas` + `dim_*`) usada por:

- Tablero (KPIs / gráficos)
- **Informes compuestos RC-01…RC-08**, publicados en ClickHouse

Después de validar el modelo estrella, el DAG ejecuta `steps/sync_clickhouse.py`. Este paso
crea el esquema `globtrade_analytics`, reemplaza sus tablas analíticas y registra el resultado
en `etl_runs`. Los RC consultan únicamente ClickHouse; no regresan silenciosamente a MongoDB.

## ¿Agregar registros o borrar y recrear?

**Este proceso hace truncate + reload (borrar y volver a crear).**

Motivos:

1. Las dimensiones regeneran IDs 1..n; un append parcial rompería FKs en `fact_ventas`.
2. Es el mismo criterio que `backend/etl/transform_fact_dimensions.py` y `POST /api/build_model`.
3. Para demo académica es reproducible e idempotente entre corridas del DAG.

**Fuera de este ETL:** el sync incremental `backend/shared/analytics_sync.py` (tras convertir
una venta en la app). Convive con Airflow; no forma parte del DAG programado.

## Pasos

| Paso | Módulo | Efecto |
|------|--------|--------|
| Extract | `steps/extract_csv.py` → `etl.csv_to_parquet` | CSV → Parquet |
| Load | `steps/load_landing.py` → `etl.load_parquet_to_mongo` | Truncate + carga `sales_records` |
| Transform | `steps/transform_star.py` → `etl.transform_fact_dimensions` | Truncate + dims + `fact_ventas` |
| Validate | `steps/validate_strategic.py` | Falla si fact/dims vacíos |

## Corrida local (sin Airflow)

```powershell
cd C:\proyect6softwa
$env:PYTHONPATH="C:\proyect6softwa;C:\proyect6softwa\backend"
$env:MONGO_URI="mongodb://localhost:27017"
$env:MONGO_DB="globtrade_dw"
$env:CSV_SOURCE="C:\proyect6softwa\data\sales.csv"
.\.venv\Scripts\python.exe -m etl_proceso.pipeline
```

### Dataset completo (~1.5M) antes de Airflow

Si `data/sales.csv` no existe o es el demo de 100k, exporta desde Mongo:

```powershell
docker compose run --rm -v "${PWD}\scripts:/app/scripts" web python scripts/export_sales_dataset.py
```

Luego **Trigger DAG** `globtrade_strategic_etl` en http://localhost:8080.

## Airflow

El DAG estratégico se ejecuta automáticamente todos los días a las **02:00** y también puede iniciarse manualmente desde Airflow.

Un solo compose (`docker-compose.yml`), profile `airflow`:

```powershell
docker compose --profile airflow up -d --build
```

- UI: http://localhost:8080 (`admin` / `admin`)
- DAG: `globtrade_strategic_etl`
- Tras un run exitoso: abrir en la web **Informes compuestos** (RC).
