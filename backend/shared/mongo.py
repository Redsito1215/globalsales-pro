"""Conexión MongoDB compartida — enrutamiento ops/DW y lecturas con réplica opcional."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson import ObjectId
from pymongo import MongoClient, ReadPreference

from config.settings import settings
from shared.db_routing import is_ops_collection


_client: MongoClient | None = None
_read_client: MongoClient | None = None


def reset_clients() -> None:
    """Cierra caches de cliente (tests / reload settings)."""
    global _client, _read_client
    if _client is not None:
        _client.close()
    if _read_client is not None:
        _read_client.close()
    _client = None
    _read_client = None


def _mongo_timeout_kwargs() -> dict[str, Any]:
    return {
        "serverSelectionTimeoutMS": int(settings.mongo_server_selection_timeout_ms or 5000),
        "connectTimeoutMS": int(settings.mongo_connect_timeout_ms or 5000),
    }


def mongo_client() -> MongoClient:
    global _client
    if _client is None:
        kwargs: dict[str, Any] = _mongo_timeout_kwargs()
        if settings.mongo_replica_set:
            kwargs["replicaSet"] = settings.mongo_replica_set
        _client = MongoClient(settings.mongo_uri, **kwargs)
    return _client


def get_ops_db_name() -> str:
    name = (settings.mongo_ops_db or "").strip()
    return name or settings.mongo_db


def get_dw_db_name() -> str:
    return settings.mongo_db


def split_enabled() -> bool:
    return get_ops_db_name() != get_dw_db_name()


def get_ops_db():
    return mongo_client()[get_ops_db_name()]


def get_dw_db():
    return mongo_client()[get_dw_db_name()]


def get_read_dw_db():
    """Lecturas analíticas; usa réplica/secundario si MONGO_REPLICA_URI está definido."""
    if settings.mongo_replica_uri:
        global _read_client
        if _read_client is None:
            kwargs: dict[str, Any] = {
                **_mongo_timeout_kwargs(),
                "readPreference": ReadPreference.SECONDARY_PREFERRED,
            }
            if settings.mongo_replica_set:
                kwargs["replicaSet"] = settings.mongo_replica_set
            _read_client = MongoClient(settings.mongo_replica_uri, **kwargs)
        return _read_client[get_dw_db_name()]
    return get_dw_db()


def get_collection(name: str):
    if is_ops_collection(name):
        return get_ops_db()[name]
    return get_dw_db()[name]


class _RoutedDatabase:
    """Proxy: db[colección] enruta a globtrade_ops o globtrade_dw."""

    @property
    def name(self) -> str:
        return get_dw_db_name()

    def __getitem__(self, name: str):
        return get_collection(name)

    def list_collection_names(self, session=None):
        ops = set(get_ops_db().list_collection_names(session=session))
        dw = set(get_dw_db().list_collection_names(session=session))
        return sorted(ops | dw)


def get_db() -> _RoutedDatabase:
    return _RoutedDatabase()


def mongo_topology() -> dict[str, Any]:
    return {
        "split_enabled": split_enabled(),
        "ops_database": get_ops_db_name(),
        "dw_database": get_dw_db_name(),
        "mongo_uri": settings.mongo_uri,
        "replica_uri": settings.mongo_replica_uri or None,
        "replica_set": settings.mongo_replica_set or None,
        "replica_reads": bool(settings.mongo_replica_uri),
    }


def json_safe(value: Any) -> Any:
    """Convierte valores BSON a tipos serializables en JSON."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def sales_collection():
    """Landing / staging (CSV, generate, post-convertir)."""
    return get_collection("sales_records")
