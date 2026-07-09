"""API FastAPI — health y futuros CRUD (puerto 8001 en host)."""
from fastapi import FastAPI

from config.settings import settings
from paquetes.tablero import queries

app = FastAPI(title="GLOBTRADE S.A. API", version="1.0.0")


@app.get("/health")
def health():
    ok = queries.ping_mongo()
    return {
        "status": "ok" if ok else "error",
        "mongo_db": settings.mongo_db,
        "paquete": "shared",
    }
