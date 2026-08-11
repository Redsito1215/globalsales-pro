# -*- coding: utf-8 -*-
"""
Orquestación Python del ETL estratégico (rebuild completo).

Estrategia: truncate + reload en landing y estrella (no append).
El sync incremental post-convertir (analytics_sync) vive fuera de este pipeline.
"""
from __future__ import annotations

import sys
from typing import Callable

from etl_proceso.steps.extract_csv import run as extract_csv
from etl_proceso.steps.load_landing import run as load_landing
from etl_proceso.steps.transform_star import run as transform_star
from etl_proceso.steps.validate_strategic import run as validate_strategic

STEPS: list[tuple[str, Callable[[], object]]] = [
    ("extract_csv_to_parquet", extract_csv),
    ("load_landing_truncate", load_landing),
    ("transform_star_rebuild", transform_star),
    ("validate_strategic_layer", validate_strategic),
]


def run_pipeline(*, stop_after: str | None = None) -> None:
    for name, fn in STEPS:
        print(f"\n=== {name} ===")
        fn()
        if stop_after and name == stop_after:
            print(f"Detenido tras {name} (stop_after).")
            return
    print("\nETL estratégico (rebuild) completado.")


if __name__ == "__main__":
    try:
        run_pipeline()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ETL falló: {exc}", file=sys.stderr)
        sys.exit(1)
