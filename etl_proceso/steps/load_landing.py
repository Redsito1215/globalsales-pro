# -*- coding: utf-8 -*-
"""Load: truncate + reload sales_records (wrapper de etl.load_parquet_to_mongo)."""
from __future__ import annotations


def run() -> None:
    from etl.load_parquet_to_mongo import main

    main()


if __name__ == "__main__":
    run()
