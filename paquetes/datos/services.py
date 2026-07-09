"""Servicios Q4 — tablas maestras."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from config.settings import ROOT, settings
from shared.audit import log_audit
from shared.master_registry import EDITABLE_MASTERS, MASTER_TABLES, get_master
from shared.mongo import get_db
from shared.shopify_registry import SHOPIFY_TABLES

ALLOWED_IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def _table_meta(name: str) -> dict[str, Any] | None:
    if name in MASTER_TABLES:
        return MASTER_TABLES[name]
    if name in SHOPIFY_TABLES:
        return SHOPIFY_TABLES[name]
    return None


def list_tables() -> list[dict[str, Any]]:
    db = get_db()
    out = []
    for name, meta in MASTER_TABLES.items():
        out.append(
            {
                "name": name,
                "label": meta["label"],
                "group": "maestros",
                "layer": "dw",
                "editable": meta.get("editable", False),
                "pk": meta["pk"],
                "count": db[name].count_documents({}),
            }
        )
    for name, meta in SHOPIFY_TABLES.items():
        try:
            count = db[name].count_documents({})
        except Exception:
            count = 0
        out.append(
            {
                "name": name,
                "label": meta["label"],
                "group": "comercio",
                "layer": meta.get("layer", "catalog"),
                "editable": meta.get("editable", False),
                "pk": meta["pk"],
                "count": count,
            }
        )
    return out


def _next_id(col, pk: str) -> int:
    row = col.find_one({}, {pk: 1, "_id": 0}, sort=[(pk, -1)])
    if not row or row.get(pk) is None:
        return 1
    return int(row[pk]) + 1


def list_rows(name: str, *, limit: int = 50, offset: int = 0, search: str | None = None) -> dict[str, Any]:
    meta = _table_meta(name)
    if not meta:
        raise ValueError("unknown_table")
    col = get_db()[name]
    query: dict[str, Any] = {}
    if search:
        or_clauses: list[dict[str, Any]] = [{"name": {"$regex": re.escape(search), "$options": "i"}}]
        if name == "dim_producto":
            or_clauses.append({"product_id": int(search) if search.isdigit() else -1})
        elif name in SHOPIFY_TABLES:
            or_clauses.append({"title": {"$regex": re.escape(search), "$options": "i"}})
            if search.isdigit():
                pk_name = meta["pk"]
                or_clauses.append({pk_name: int(search)})
        query["$or"] = or_clauses
    total = col.count_documents(query)
    pk = meta["pk"]
    rows = list(col.find(query, {"_id": 0}).sort(pk, 1).skip(offset).limit(limit))
    return {
        "name": name,
        "label": meta["label"],
        "group": "comercio" if name in SHOPIFY_TABLES else "maestros",
        "layer": meta.get("layer"),
        "editable": meta.get("editable", False) and name in EDITABLE_MASTERS,
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": rows,
    }


def get_row(name: str, row_id: str) -> dict[str, Any] | None:
    meta = _table_meta(name)
    if not meta:
        raise ValueError("unknown_table")
    pk = meta["pk"]
    try:
        key: Any = int(row_id)
    except ValueError:
        key = row_id
    return get_db()[name].find_one({pk: key}, {"_id": 0})


def create_row(name: str, data: dict[str, Any]) -> dict[str, Any]:
    if name not in EDITABLE_MASTERS:
        raise ValueError("read_only")
    meta = get_master(name)
    assert meta
    col = get_db()[name]
    pk = meta["pk"]
    doc = {k: data[k] for k in meta["fields"] if k in data and k != pk}
    if pk not in data or not data.get(pk):
        doc[pk] = _next_id(col, pk)
    else:
        doc[pk] = int(data[pk]) if str(data[pk]).isdigit() else data[pk]
    if col.find_one({pk: doc[pk]}):
        raise ValueError("duplicate_pk")
    if name == "dim_producto":
        up, uc = float(doc.get("unit_price") or 0), float(doc.get("unit_cost") or 0)
        doc.setdefault("margin_pct", round(((up - uc) / up * 100) if up else 0, 2))
        doc.setdefault("units", 0)
        doc.setdefault("orders", 0)
        doc.setdefault("revenue", 0.0)
        doc.setdefault("line", int(doc.get("line") or 1))
        doc.setdefault("image_url", None)
    if name == "dim_cliente":
        doc.setdefault("created_at", date.today().isoformat())
    col.insert_one(doc)
    log_audit("create", entity=name, entity_id=doc[pk], details={"pk": doc[pk]})
    return {k: v for k, v in doc.items()}


def update_row(name: str, row_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if name not in EDITABLE_MASTERS:
        raise ValueError("read_only")
    meta = get_master(name)
    assert meta
    pk = meta["pk"]
    try:
        key: Any = int(row_id)
    except ValueError:
        key = row_id
    col = get_db()[name]
    existing = col.find_one({pk: key})
    if not existing:
        raise ValueError("not_found")
    patch = {k: data[k] for k in meta["fields"] if k in data and k != pk}
    if name == "dim_producto" and ("unit_price" in patch or "unit_cost" in patch):
        up = float(patch.get("unit_price", existing.get("unit_price") or 0))
        uc = float(patch.get("unit_cost", existing.get("unit_cost") or 0))
        patch["margin_pct"] = round(((up - uc) / up * 100) if up else 0, 2)
    col.update_one({pk: key}, {"$set": patch})
    log_audit("update", entity=name, entity_id=key, details=patch)
    updated = col.find_one({pk: key}, {"_id": 0})
    return dict(updated) if updated else {}


def delete_row(name: str, row_id: str) -> None:
    if name not in EDITABLE_MASTERS:
        raise ValueError("read_only")
    meta = get_master(name)
    assert meta
    pk = meta["pk"]
    try:
        key: Any = int(row_id)
    except ValueError:
        key = row_id
    col = get_db()[name]
    if not col.find_one({pk: key}):
        raise ValueError("not_found")
    _check_delete_refs(name, key)
    col.delete_one({pk: key})
    log_audit("delete", entity=name, entity_id=key)


def _check_delete_refs(name: str, key: Any) -> None:
    db = get_db()
    if name == "dim_region" and db["dim_pais"].count_documents({"region_id": key}):
        raise ValueError("has_children")
    if name == "dim_categoria" and db["dim_producto"].count_documents({"category_id": key}):
        raise ValueError("has_children")
    if name == "dim_pais" and db["dim_cliente"].count_documents({"country_id": key}):
        raise ValueError("has_children")


def save_product_image(product_id: int, filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValueError("invalid_image_type")
    max_bytes = settings.max_product_image_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValueError("image_too_large")
    col = get_db()["dim_producto"]
    prod = col.find_one({"product_id": int(product_id)})
    if not prod:
        raise ValueError("not_found")
    dest_dir = settings.product_uploads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{int(product_id)}_{uuid.uuid4().hex[:8]}{ext}"
    path = dest_dir / safe_name
    path.write_bytes(raw)
    url = f"/static/uploads/products/{safe_name}"
    col.update_one({"product_id": int(product_id)}, {"$set": {"image_url": url, "image_source": "upload"}})
    log_audit("upload_image", entity="dim_producto", entity_id=product_id, details={"image_url": url})
    return url


def run_build_model() -> dict[str, Any]:
    from etl.transform_fact_dimensions import main as build_main

    build_main(mongo_uri=settings.mongo_uri, mongo_db=settings.mongo_db)
    log_audit("build_model", entity="etl", details={"mongo_db": settings.mongo_db})
    db = get_db()
    return {
        "sales_records": db["sales_records"].count_documents({}),
        "fact_ventas": db["fact_ventas"].count_documents({}),
        "dim_producto": db["dim_producto"].count_documents({}),
    }


def run_load_dataset(csv_path: str | None = None) -> dict[str, Any]:
    csv = Path(csv_path) if csv_path else settings.csv_source
    if not csv.is_absolute():
        csv = ROOT / csv
    if not csv.exists():
        raise ValueError("csv_not_found")

    env = dict(os.environ)
    env["CSV_SOURCE"] = str(csv)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "backend"), str(ROOT)])
    steps = ("etl.csv_to_parquet", "etl.load_parquet_to_mongo", "etl.transform_fact_dimensions")
    for step in steps:
        proc = subprocess.run(
            [sys.executable, "-m", step],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or f"Fallo en {step}")

    log_audit("load_dataset", entity="etl", details={"csv": str(csv)})
    db = get_db()
    return {
        "message": "Dataset cargado y modelo reconstruido.",
        "sales_records": db["sales_records"].count_documents({}),
        "fact_ventas": db["fact_ventas"].count_documents({}),
    }


def get_elt_status() -> dict[str, Any]:
    db = get_db()
    pq = settings.data_parquet_dir / "sales_records.parquet"
    counts = {}
    for name in list(MASTER_TABLES.keys()) + ["sales_records", "fact_ventas", "purchase_requests", "audit_log"]:
        try:
            counts[name] = db[name].count_documents({})
        except Exception:
            counts[name] = 0
    return {
        "mongo_db": settings.mongo_db,
        "mongo_uri": settings.mongo_uri.split("@")[-1],
        "parquet": str(pq),
        "parquet_exists": pq.exists(),
        "csv_source": str(settings.csv_source),
        "csv_exists": settings.csv_source.exists(),
        "counts": counts,
    }


def list_audit_log(*, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    col = get_db()["audit_log"]
    total = col.count_documents({})
    rows = list(col.find({}, {"_id": 0}).sort("at", -1).skip(offset).limit(limit))
    return {"total": total, "limit": limit, "offset": offset, "entries": rows}
