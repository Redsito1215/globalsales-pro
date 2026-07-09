"""CSV → Parquet (sin PocketBase). Para Docker / carga directa."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

from config.settings import settings


def main() -> None:
    raw = os.environ.get("CSV_SOURCE")
    src = Path(raw) if raw else settings.csv_source
    if not src.exists():
        print(f"No existe CSV: {src}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(src)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for col in ("order_date", "ship_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%m/%d/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
    if "order_id" in df.columns:
        df["order_id"] = df["order_id"].astype(str)

    settings.data_parquet_dir.mkdir(parents=True, exist_ok=True)
    out = settings.data_parquet_dir / f"{settings.pocketbase_collection}.parquet"
    df.to_parquet(out, index=False, engine="pyarrow")
    print(f"Parquet: {out} ({len(df):,} filas)")


if __name__ == "__main__":
    main()
