# -*- coding: utf-8 -*-
"""Arranque y migración automática ops/DW (globtrade_ops + globtrade_dw)."""
from __future__ import annotations

from typing import Any

from shared.db_routing import OPS_COLLECTIONS
from shared.mongo import (
    get_dw_db_name,
    get_ops_db,
    get_ops_db_name,
    mongo_client,
    split_enabled,
)


def _ops_needs_bootstrap() -> bool:
    """True si split activo, ops vacío y DW aún tiene colecciones operativas."""
    if not split_enabled():
        return False
    ops = get_ops_db()
    if ops["users"].count_documents({}, limit=1) or ops["purchase_requests"].count_documents({}, limit=1):
        return False
    dw = mongo_client()[get_dw_db_name()]
    for coll in ("users", "purchase_requests", "products"):
        if coll in dw.list_collection_names() and dw[coll].count_documents({}, limit=1):
            return True
    return False


def bootstrap_ops_from_dw(*, drop_source: bool = False) -> dict[str, Any]:
    """Copia colecciones operativas/gobernanza desde DW hacia globtrade_ops."""
    if not split_enabled():
        return {"ok": False, "reason": "single_db", "moved": 0}

    client = mongo_client()
    src = client[get_dw_db_name()]
    dst = client[get_ops_db_name()]
    moved = 0
    collections = 0

    for coll in sorted(OPS_COLLECTIONS):
        if coll not in src.list_collection_names():
            continue
        count = src[coll].count_documents({})
        if count <= 0:
            continue
        collections += 1
        for doc in src[coll].find({}):
            dst[coll].replace_one({"_id": doc["_id"]}, doc, upsert=True)
        moved += count
        if drop_source:
            src[coll].drop()

    return {
        "ok": True,
        "moved": moved,
        "collections": collections,
        "ops_database": get_ops_db_name(),
        "dw_database": get_dw_db_name(),
        "drop_source": drop_source,
    }


def ensure_ops_split_bootstrap() -> dict[str, Any]:
    """En arranque: migra ops desde DW si hace falta (sin borrar DW)."""
    if not split_enabled():
        return {"skipped": True, "reason": "single_db"}
    if not _ops_needs_bootstrap():
        return {"skipped": True, "reason": "ops_ready"}
    result = bootstrap_ops_from_dw(drop_source=False)
    result["auto"] = True
    return result
