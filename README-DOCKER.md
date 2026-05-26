# Docker — GLOBTRADE S.A.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y **en ejecución**
- Archivo `.env` en la raíz del proyecto (copiar desde `.env.example`)

## 1. Preparar datos en el host

```powershell
cd C:\vicuna
mkdir data\parquet, data\raw, frontend\static -Force
copy C:\import\sales_records.csv data\sales.csv
```

Los HTML del dashboard ya están en `frontend\static\`.

Si ya tienes Parquet del ELT local:

```powershell
copy C:\Users\redsito\.cursor\projects\empty-window\globtrade-elt\data\parquet\sales_records.parquet data\parquet\
```

## 2. Configurar `.env` para Docker

```env
MONGO_URI=mongodb://mongo:27017
MONGO_DB=globtrade_dw
POCKETBASE_COLLECTION=sales_records
CSV_SOURCE=/app/data/sales.csv
```

> En el host (sin Docker) usa `mongodb://localhost:27017`.

## 3. Levantar todo

```powershell
docker compose up -d --build
```

| Servicio | URL |
|----------|-----|
| Dashboard | http://localhost:5000 |
| API CRUD | http://localhost:8000/docs |
| MongoDB | localhost:27017 |

## 4. Ejecutar ELT dentro de Docker

```powershell
docker compose --profile etl-mongo run --rm etl-mongo
```

Resultado en el host:

```text
data\parquet\sales_records.parquet
```

Y en MongoDB: `sales_records`, `fact_ventas`, `regions`, `orders`, etc.

## 5. Comandos útiles

```powershell
docker compose ps
docker compose logs -f api
docker compose logs -f web
docker compose down
docker compose down -v   # borra volúmenes (cuidado)
```

## Arquitectura

```text
CSV → data/parquet (Parquet)
     ↓
MongoDB :27017
     ↓
fact_ventas + dim_* + sales_records ...
     ↓
API :8000  +  Web :5000
```

> Lo relacionado con PocketBase está en `eliminar/`.
