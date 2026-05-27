# GLOBTRADE S.A. — Kiro · MongoDB · Docker Desktop

Proyecto unificado: **ELT → MongoDB**, **API CRUD**, **dashboard web**.

## Estructura (ordenada para Kiro)

```text
C:\vicuna\
├── .kiro\specs\
│   ├── globtrade-mongodb\      ← Pozo / ELT (NO DuckDB)
│   └── globtrade-web-platform\ ← Dashboard Flask
├── .venv\                      ← un solo entorno (crear en raíz)
├── .vscode\                    ← PYTHONPATH → backend
├── backend\
│   ├── api\                    ← FastAPI :8000
│   ├── config\
│   └── etl\
├── frontend\
│   ├── app.py                  ← Dashboard :5000
│   ├── mongo_manager.py
│   └── static\
├── data\
│   ├── raw\
│   ├── parquet\
│   └── sales.csv
├── eliminar\                   ← copia de lo obsoleto (puedes borrarla)
├── scripts\
├── .env / .env.example
├── docker-compose.yml
├── Dockerfile
├── README-DOCKER.md
└── requirements.txt
```

## Inicio rápido (local)

```powershell
cd C:\vicuna
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
$env:PYTHONPATH = "$PWD\backend"

# ELT sin PocketBase (recomendado)
python -m etl.run_pipeline_mongo

# API
uvicorn api.main:app --reload

# Dashboard
python frontend\app.py
```

## Docker Desktop (solo desde esta carpeta)

**No uses `C:\globtrade`.** Esa carpeta era una copia antigua; todo corre aquí en `C:\vicuna`:

```powershell
cd C:\vicuna
docker compose up -d --build
docker compose --profile etl-mongo run --rm etl-mongo
```

Si Docker Desktop aún apunta a `C:\globtrade`, ejecuta una vez:

```powershell
.\scripts\docker-unificar.ps1
```

Ver detalles en [README-DOCKER.md](README-DOCKER.md).

## Kiro

Abre en Kiro la spec que corresponda:

- **Datos / MongoDB**: `.kiro/specs/globtrade-mongodb/`
- **Web**: `.kiro/specs/globtrade-web-platform/`

Ejecuta el dashboard desde `frontend/app.py` (no desde la carpeta antigua `files/`).


