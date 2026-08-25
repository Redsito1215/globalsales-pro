"""Exportación CSV segura y consistente para informes."""
from __future__ import annotations

import csv
import io
from typing import Any

from paquetes.reportes.pdf_export import COLUMN_LABELS


def safe_csv_value(value: Any) -> Any:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def generate_report_csv(*, columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([COLUMN_LABELS.get(col, col) for col in columns])
    for row in rows:
        writer.writerow([safe_csv_value(row.get(col)) for col in columns])
    return ("\ufeff" + stream.getvalue()).encode("utf-8")

