# -*- coding: utf-8 -*-
"""
DAG: ETL estratégico GLOBTRADE → fact_ventas + dims (informes RC / Tablero).

Estrategia: truncate + reload (no append). Schedule diario; catchup desactivado.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Repo montado en el contenedor (ver docker-compose.yml, profile airflow)
_PROJECT = Path(os.environ.get("GLOBTRADE_PROJECT", "/opt/airflow/project"))
for p in (_PROJECT, _PROJECT / "backend"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

default_args = {
    "owner": "globtrade",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _task_extract() -> None:
    from etl_proceso.steps.extract_csv import run

    run()


def _task_load() -> None:
    from etl_proceso.steps.load_landing import run

    run()


def _task_transform() -> None:
    from etl_proceso.steps.transform_star import run

    run()


def _task_validate() -> None:
    from etl_proceso.steps.validate_strategic import run

    run()


with DAG(
    dag_id="globtrade_strategic_etl",
    description="ETL estratégico rebuild: CSV→Parquet→sales_records→fact_ventas (RC/Tablero)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    tags=["globtrade", "etl", "estrategico", "reportes-rc"],
    max_active_runs=1,
) as dag:
    extract_csv_to_parquet = PythonOperator(
        task_id="extract_csv_to_parquet",
        python_callable=_task_extract,
    )
    load_landing_truncate = PythonOperator(
        task_id="load_landing_truncate",
        python_callable=_task_load,
    )
    transform_star_rebuild = PythonOperator(
        task_id="transform_star_rebuild",
        python_callable=_task_transform,
    )
    validate_strategic_layer = PythonOperator(
        task_id="validate_strategic_layer",
        python_callable=_task_validate,
    )

    (
        extract_csv_to_parquet
        >> load_landing_truncate
        >> transform_star_rebuild
        >> validate_strategic_layer
    )
