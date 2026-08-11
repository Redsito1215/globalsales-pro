# -*- coding: utf-8 -*-
"""Pasos del ETL estratégico (wrappers sobre backend/etl)."""

from etl_proceso.steps.extract_csv import run as extract_csv
from etl_proceso.steps.load_landing import run as load_landing
from etl_proceso.steps.transform_star import run as transform_star
from etl_proceso.steps.validate_strategic import run as validate_strategic

__all__ = [
    "extract_csv",
    "load_landing",
    "transform_star",
    "validate_strategic",
]
