# -*- coding: utf-8 -*-
"""Pasos idempotentes del DAG manual usado en presentación.

La fuente oficial es ``sales_records`` en Mongo. Ningún paso borra la landing
ni reconstruye dos millones de hechos en memoria; únicamente se sincronizan
pedidos recientes pendientes y luego se valida la capa estratégica.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from pymongo import MongoClient


def _db():
    uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    name = os.getenv("MONGO_DB") or "globtrade_dw"
    client = MongoClient(uri, serverSelectionTimeoutMS=8_000, connectTimeoutMS=8_000)
    client.admin.command("ping")
    return client, client[name]


def inspect_landing() -> dict:
    """Comprueba la fuente actual sin exportarla ni sustituirla por el CSV."""
    client, db = _db()
    try:
        count = int(db["sales_records"].estimated_document_count())
        if count <= 0:
            raise RuntimeError("sales_records está vacío; se cancela sin modificar datos.")
        sample = db["sales_records"].find_one({}, {"_id": 0}) or {}
        required = {"order_id", "order_date", "region", "country", "item_type"}
        missing = sorted(required - set(sample))
        if missing:
            raise RuntimeError(f"Fuente landing inválida; faltan campos: {', '.join(missing)}")
        result = {"sales_records": count, "source": "mongo", "checked_at": datetime.now(timezone.utc).isoformat()}
        db["app_meta"].update_one({"_id": "airflow_safe_run"}, {"$set": result}, upsert=True)
        print(f"Fuente Mongo verificada — sales_records={count:,}")
        return result
    finally:
        client.close()


def preserve_landing() -> dict:
    """Confirma que la landing sigue disponible; este paso nunca hace truncate."""
    client, db = _db()
    try:
        before = (db["app_meta"].find_one({"_id": "airflow_safe_run"}) or {}).get("sales_records")
        current = int(db["sales_records"].estimated_document_count())
        if current <= 0 or (before is not None and int(before) != current):
            raise RuntimeError("La landing cambió durante la ejecución; se cancela sin borrar datos.")
        db["sales_records"].create_index([("order_id", 1)], name="sales_order")
        print(f"Landing preservada — sales_records={current:,}; no se ejecutó truncate")
        return {"sales_records": current, "preserved": True}
    finally:
        client.close()


def synchronize_strategic() -> dict:
    """Sincroniza solo pedidos recientes ausentes y exige paridad al finalizar."""
    client, db = _db()
    try:
        landing = int(db["sales_records"].estimated_document_count())
        facts_before = int(db["fact_ventas"].estimated_document_count())
    finally:
        client.close()

    sync_result = {"orders_synced": [], "facts_inserted": 0}
    if facts_before < landing:
        from shared.analytics_sync import sync_stale_orders

        sync_result = sync_stale_orders(limit=500)

    client, db = _db()
    try:
        facts_after = int(db["fact_ventas"].estimated_document_count())
        if facts_after != landing:
            raise RuntimeError(
                f"Paridad pendiente: sales_records={landing:,}, fact_ventas={facts_after:,}. "
                "Se conservan ambas colecciones; no se realizó reconstrucción destructiva."
            )
        from shared.analytics_sync import set_strategic_lag
        from shared.ops_indexes import ensure_ops_indexes

        set_strategic_lag(False, detail="Airflow manual: capa estratégica verificada")
        ensure_ops_indexes()
        print(f"Capa estratégica sincronizada — fact_ventas={facts_after:,}")
        return {**sync_result, "sales_records": landing, "fact_ventas": facts_after}
    finally:
        client.close()
