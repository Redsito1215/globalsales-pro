# -*- coding: utf-8 -*-
"""Exporta sales_records (Mongo) → data/sales.csv + data/parquet/sales_records.parquet.

Necesario antes de lanzar el DAG Airflow con el dataset completo (~1.5M filas).
El ETL hace truncate+reload; sin este archivo, Airflow puede cargar un CSV demo chico.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
BATCH = 25_000

CSV_FIELDS = (
    "order_id",
    "order_date",
    "ship_date",
    "region",
    "country",
    "item_type",
    "sales_channel",
    "order_priority",
    "units_sold",
    "unit_price",
    "unit_cost",
    "total_revenue",
    "total_cost",
    "total_profit",
)


def _fmt_us_date(value) -> str:
    if value is None or value == "":
        return ""
    s = str(value)[:10]
    if len(s) == 10 and s[4] == "-":
        y, m, d = s.split("-")
        return f"{int(m)}/{int(d)}/{y}"
    return str(value)


def main() -> None:
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB", "globtrade_dw")
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    col = client[db_name]["sales_records"]
    total = col.estimated_document_count()
    if total < 1:
        print("sales_records vacío — no hay nada que exportar.", file=sys.stderr)
        sys.exit(1)

    parquet_path = ROOT / "data" / "parquet" / "sales_records.parquet"
    csv_path = ROOT / "data" / "sales.csv"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exportando {total:,} filas desde {db_name}.sales_records …")
    writer: pq.ParquetWriter | None = None
    written = 0
    csv_file = csv_path.open("w", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
    csv_writer.writeheader()

    batch: list[dict] = []
    for doc in col.find({}, {"_id": 0, "id": 0}):
        row = {k: doc.get(k) for k in CSV_FIELDS}
        if row.get("order_id") is not None:
            row["order_id"] = str(row["order_id"])
        row["order_date"] = _fmt_us_date(row.get("order_date"))
        row["ship_date"] = _fmt_us_date(row.get("ship_date"))
        batch.append(row)
        if len(batch) < BATCH:
            continue

        table = pa.Table.from_pylist(batch)
        if writer is None:
            writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.write_table(table)
        for r in batch:
            csv_writer.writerow({k: r.get(k, "") for k in CSV_FIELDS})
        written += len(batch)
        print(f"  {written:,}/{total:,}")
        batch = []

    if batch:
        table = pa.Table.from_pylist(batch)
        if writer is None:
            writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.write_table(table)
        for r in batch:
            csv_writer.writerow({k: r.get(k, "") for k in CSV_FIELDS})
        written += len(batch)
        print(f"  {written:,}/{total:,}")

    if writer is not None:
        writer.close()
    csv_file.close()
    client.close()

    if written != total:
        print(f"Advertencia: exportadas {written:,} vs estimadas {total:,}", file=sys.stderr)
    try:
        os.chmod(parquet_path, 0o666)
        os.chmod(csv_path, 0o666)
        os.chmod(parquet_path.parent, 0o777)
    except OSError:
        pass
    print(f"OK parquet → {parquet_path}")
    print(f"OK csv     → {csv_path}")


if __name__ == "__main__":
    main()
