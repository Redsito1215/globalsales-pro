"""Paso 3 — CARGAR Parquet → MongoDB (staging)."""
from __future__ import annotations

import sys

import pandas as pd
from pymongo import MongoClient

from config.settings import settings

BATCH = 5000


def main() -> None:
    parquet = settings.data_parquet_dir / f"{settings.pocketbase_collection}.parquet"
    if not parquet.exists():
        print("Ejecute: python -m etl.run_pipeline_mongo", file=sys.stderr)
        sys.exit(1)
    df = pd.read_parquet(parquet)
    for col in ("order_date", "ship_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
    if "order_id" in df.columns:
        df["order_id"] = df["order_id"].astype(str)
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    col = client[settings.mongo_db]["sales_records"]
    col.delete_many({})
    records = df.to_dict(orient="records")
    for i in range(0, len(records), BATCH):
        col.insert_many(records[i : i + BATCH], ordered=False)
        print(f"  {min(i + BATCH, len(records))}/{len(records)}")
    print(f"sales_records: {col.count_documents({})}")
    client.close()


if __name__ == "__main__":
    main()
