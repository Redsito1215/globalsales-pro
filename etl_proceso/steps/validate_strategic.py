# -*- coding: utf-8 -*-
"""Validate: capa estratégica lista para Tablero e Informes compuestos RC."""
from __future__ import annotations

import os
import sys

from pymongo import MongoClient

REQUIRED_DIMS = (
    "dim_region",
    "dim_pais",
    "dim_categoria",
    "dim_producto",
    "dim_canal",
    "dim_prioridad",
    "dim_cliente",
    "dim_tiempo",
)


def run() -> dict:
    uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    db_name = os.getenv("MONGO_DB") or "globtrade_dw"
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
        db = client[db_name]
        fact_n = int(db["fact_ventas"].estimated_document_count())
        if fact_n <= 0:
            raise RuntimeError(
                "fact_ventas vacío tras el ETL — los informes RC / Tablero no tendrán datos."
            )
        missing = []
        counts: dict[str, int] = {"fact_ventas": fact_n}
        for name in REQUIRED_DIMS:
            n = int(db[name].estimated_document_count())
            counts[name] = n
            if n <= 0:
                missing.append(name)
        if missing:
            raise RuntimeError(f"Dimensiones vacías: {', '.join(missing)}")
        landing = int(db["sales_records"].estimated_document_count())
        counts["sales_records"] = landing
        print(
            "Validación OK — "
            f"fact_ventas={fact_n:,} sales_records={landing:,} "
            + " ".join(f"{k}={counts[k]:,}" for k in REQUIRED_DIMS[:4])
        )
        return counts
    finally:
        client.close()


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
