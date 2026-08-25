# -*- coding: utf-8 -*-
"""
DAG: validación y sincronización segura GLOBTRADE → fact_ventas.

Estrategia idempotente: Mongo landing → sincronización pendiente → validación.
No usa el CSV antiguo y no elimina colecciones. Ejecución exclusivamente manual.
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


def _task_inspect() -> None:
    from etl_proceso.steps.airflow_safe import inspect_landing

    inspect_landing()


def _task_preserve() -> None:
    from etl_proceso.steps.airflow_safe import preserve_landing

    preserve_landing()


def _task_transform() -> None:
    from etl_proceso.steps.airflow_safe import synchronize_strategic

    synchronize_strategic()


def _task_validate() -> None:
    from etl_proceso.steps.validate_strategic import run

    run()


with DAG(
    dag_id="globtrade_strategic_etl",
    description="ETL manual seguro: Mongo landing→sincronización→validación (RC/Tablero)",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["globtrade", "etl", "estrategico", "reportes-rc"],
    max_active_runs=1,
) as dag:
    inspect_mongo_landing = PythonOperator(
        task_id="inspect_mongo_landing",
        python_callable=_task_inspect,
    )
    preserve_landing_dataset = PythonOperator(
        task_id="preserve_landing_dataset",
        python_callable=_task_preserve,
    )
    synchronize_strategic_layer = PythonOperator(
        task_id="synchronize_strategic_layer",
        python_callable=_task_transform,
    )
    validate_strategic_layer = PythonOperator(
        task_id="validate_strategic_layer",
        python_callable=_task_validate,
    )

    (
        inspect_mongo_landing
        >> preserve_landing_dataset
        >> synchronize_strategic_layer
        >> validate_strategic_layer
    )
