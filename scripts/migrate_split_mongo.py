#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Separa colecciones operativas/gobernanza hacia globtrade_ops (desde globtrade_dw).

Requisito: MONGO_OPS_DB distinto de MONGO_DB (p. ej. globtrade_ops vs globtrade_dw).

Uso:
  python scripts/migrate_split_mongo.py
  python scripts/migrate_split_mongo.py --drop-source
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from config.settings import settings  # noqa: E402
from shared.db_routing import OPS_COLLECTIONS  # noqa: E402
from shared.mongo import get_dw_db_name, get_ops_db_name, mongo_client, split_enabled  # noqa: E402


def migrate(*, drop_source: bool) -> int:
    if not split_enabled():
        print(
            "Modo base única activo. Define MONGO_OPS_DB=globtrade_ops y MONGO_DB=globtrade_dw.",
            file=sys.stderr,
        )
        return 1

    client = mongo_client()
    src_name = get_dw_db_name()
    dst_name = get_ops_db_name()
    src = client[src_name]
    dst = client[dst_name]

    print(f"Migración {src_name} → {dst_name}")
    moved = 0
    for coll in sorted(OPS_COLLECTIONS):
        if coll not in src.list_collection_names():
            continue
        count = src[coll].count_documents({})
        if count == 0:
            continue
        print(f"  · {coll}: {count} documento(s)")
        batch = []
        for doc in src[coll].find({}):
            batch.append(doc)
            if len(batch) >= 500:
                for item in batch:
                    dst[coll].replace_one({"_id": item["_id"]}, item, upsert=True)
                batch.clear()
        for item in batch:
            dst[coll].replace_one({"_id": item["_id"]}, item, upsert=True)
        moved += count
        if drop_source:
            src[coll].drop()
            print(f"    ↳ eliminada de {src_name}")

    print(f"\nListo: {moved} documento(s) en {len(OPS_COLLECTIONS)} colecciones ops/gobernanza.")
    if not drop_source:
        print("Los datos siguen también en la DW hasta que ejecutes --drop-source.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Split Mongo ops/DW GLOBTRADE")
    parser.add_argument(
        "--drop-source",
        action="store_true",
        help="Elimina colecciones ops de la base DW tras copiar",
    )
    args = parser.parse_args()
    try:
        return migrate(drop_source=args.drop_source)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
