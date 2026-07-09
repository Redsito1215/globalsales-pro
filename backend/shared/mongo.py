"""Conexión MongoDB compartida (misma instancia que vicuna)."""
from pymongo import MongoClient

from config.settings import settings


def get_db():
    return MongoClient(settings.mongo_uri)[settings.mongo_db]


def sales_collection():
    return get_db()["sales_records"]
