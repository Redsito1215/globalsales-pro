# -*- coding: utf-8 -*-
"""Extract: CSV → Parquet (wrapper de etl.csv_to_parquet)."""
from __future__ import annotations


def run() -> None:
    from etl.csv_to_parquet import main

    main()


if __name__ == "__main__":
    run()
