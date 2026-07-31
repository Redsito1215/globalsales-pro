"""Conexión MongoDB compartida (misma instancia que vicuna)."""
from pymongo import MongoClient

from config.settings import settings


def get_db():
    return MongoClient(settings.mongo_uri)[settings.mongo_db]


def sales_collection():
    """Landing / staging (CSV, generate, post-convertir).

    Capas operativo/estratégico: importar desde ``shared.data_layers``
    (no reexportar aquí para evitar import circular).
    """
    return get_db()["sales_records"]
