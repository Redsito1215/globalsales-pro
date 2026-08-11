# Quickstart: Plataforma Web GLOBTRADE

## Prerequisites

- Docker Desktop running.
- MongoDB container `globtrade-mongo` available from `C:\vicuna`.
- Python 3.12+ for local execution.
- Project root: `C:\proyect6softwa`.

## Start MongoDB

```powershell
cd C:\vicuna
docker compose up -d mongo
```

## Prepare Local App

```powershell
cd C:\proyect6softwa
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "C:\proyect6softwa\backend;C:\proyect6softwa"
python frontend\app.py
```

Open: http://127.0.0.1:5001

## Validation Scenarios

### Q1 Tablero

1. Open http://127.0.0.1:5001.
2. Select period "Todo el historico".
3. Confirm KPIs, charts, and table show non-empty historical data.
4. Change filters for region, product, channel, and priority.
5. Confirm visible data updates without page errors.

### Access

1. Use the login/register UI or call `/api/auth/register`.
2. Confirm `/api/auth/me` returns `authenticated: true`.
3. Log out and confirm `/api/auth/me` returns `authenticated: false`.
4. Try a protected action without a session and confirm it is rejected.

### Q3 Ventas

1. Open the Ventas menu.
2. Filter and paginate orders.
3. Open an order detail.
4. Confirm create/edit/delete actions require administrator permissions.

### Q2 Informes

1. Open Informes.
2. Review Tendencias, Regiones, and Productos.
3. Confirm each view respects the historical period.
4. Confirm export requires session.

### Q4 Datos

1. Open Datos.
2. List master tables and inspect one collection.
3. Review schema/model cards and Mongo status.
4. Confirm build/load actions require administrator permissions.

## Docker Validation

```cmd
cd C:\proyect6softwa
scripts\docker-up.cmd
```

Open: http://127.0.0.1:5001

Expected result: web container serves the SPA, Mongo connection points to
`host.docker.internal:27017`, and the dashboard can read `globtrade_dw`.

## Airflow ETL (capa estratégica / RC)

Orquesta rebuild truncate+reload hacia `fact_ventas` (Informes compuestos RC, sin IA).
Mismo `docker-compose.yml` del proyecto (profile `airflow`):

```powershell
cd C:\proyect6softwa
docker compose --profile airflow up -d --build
```

1. Open http://localhost:8080 (admin / admin).
2. Unpause and Trigger DAG `globtrade_strategic_etl`.
3. Confirm tasks extract → load → transform → validate succeed.
4. Open Informes compuestos RC in the web app and verify RC-08 / RC-01.
