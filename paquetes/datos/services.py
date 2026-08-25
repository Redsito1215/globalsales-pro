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
from shared.master_registry import EDITABLE_MASTERS, MASTER_TABLES, field_label, get_master, master_allows_create
from shared.mongo import get_db, json_safe
from shared.shopify_registry import SHOPIFY_TABLES

ALLOWED_IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def _table_meta(name: str) -> dict[str, Any] | None:
    if name in MASTER_TABLES:
        return MASTER_TABLES[name]
    if name in SHOPIFY_TABLES:
        return SHOPIFY_TABLES[name]
    return None


def list_editable_masters() -> list[dict[str, Any]]:
    """Tablas maestras dim_* editables desde Datos Q4 (sin comercio ni dims generadas por ELT)."""
    db = get_db()
    out: list[dict[str, Any]] = []
    for name in EDITABLE_MASTERS:
        meta = MASTER_TABLES[name]
        out.append(
            {
                "name": name,
                "label": meta["label"],
                "description": meta.get("description", ""),
                "group": "gestion",
                "layer": "dw",
                "editable": True,
                "creatable": master_allows_create(name),
                "pk": meta["pk"],
                "fields": meta.get("fields", []),
                "count": db[name].count_documents({}),
            }
        )
    return out


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


def list_rows(
    name: str,
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    meta = _table_meta(name)
    if not meta:
        raise ValueError("unknown_table")
    col = get_db()[name]
    query: dict[str, Any] = {}
    if name in EDITABLE_MASTERS and active is not None:
        query["active"] = {"$ne": False} if active else False
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
    if name in EDITABLE_MASTERS:
        for row in rows:
            row.setdefault("active", True)
    if name == "dim_producto":
        for row in rows:
            row.setdefault("sale_enabled", False)
            row.setdefault("sale_percent", 25)
    return {
        "name": name,
        "label": meta["label"],
        "description": meta.get("description", ""),
        "group": "comercio" if name in SHOPIFY_TABLES else "gestion",
        "layer": meta.get("layer"),
        "editable": meta.get("editable", False) and name in EDITABLE_MASTERS,
        "total": total,
        "limit": limit,
        "offset": offset,
        "columns": meta.get("fields") or (list(rows[0].keys()) if rows else []),
        "field_labels": {f: field_label(f) for f in (meta.get("fields") or [])},
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


def _validate_master_row(name: str, doc: dict[str, Any], *, partial: bool = False) -> None:
    int_positive = {"category_id", "region_id", "country_id", "channel_id", "line", "sla_days", "product_id"}
    float_positive = {"unit_price", "unit_cost"}
    for field in int_positive:
        if field not in doc:
            if partial:
                continue
            if name == "dim_producto" and field == "product_id":
                continue
            if name == "dim_cliente" and field in ("country_id", "channel_id") and doc.get(field) is None:
                continue
            continue
        val = doc.get(field)
        if val is None or val == "":
            if partial:
                continue
            raise ValueError("invalid_field")
        try:
            n = int(val)
        except (TypeError, ValueError):
            raise ValueError("invalid_field")
        if n < 1:
            raise ValueError("invalid_field")
    for field in float_positive:
        if field not in doc:
            continue
        val = doc.get(field)
        if val is None or val == "":
            if partial:
                continue
            raise ValueError("invalid_field")
        try:
            n = float(val)
        except (TypeError, ValueError):
            raise ValueError("invalid_field")
        if n <= 0:
            raise ValueError("invalid_field")
    name_val = doc.get("name")
    if name_val is not None and not str(name_val).strip():
        raise ValueError("invalid_field")


def _check_master_duplicates(name: str, doc: dict[str, Any], *, exclude_key: Any | None = None) -> None:
    meta = get_master(name)
    if not meta:
        return
    unique_fields = {
        "dim_region": ("name",), "dim_pais": ("name",), "dim_categoria": ("name",),
        "dim_producto": ("name",), "dim_canal": ("name",), "dim_prioridad": ("code", "name"),
        "dim_cliente": ("email",),
    }.get(name, ())
    pk = meta["pk"]
    col = get_db()[name]
    for field in unique_fields:
        value = doc.get(field)
        if value in (None, ""):
            continue
        query: dict[str, Any] = {
            field: {"$regex": f"^{re.escape(str(value).strip())}$", "$options": "i"}
        }
        if exclude_key is not None:
            query[pk] = {"$ne": exclude_key}
        if col.find_one(query, {pk: 1}):
            raise ValueError("duplicate_value")


def _sync_shop_after_master_change(name: str) -> None:
    """Mantiene vitrina alineada con dim_categoria / dim_producto tras editar maestros."""
    if name not in ("dim_categoria", "dim_producto", "dim_cliente"):
        return
    try:
        from paquetes.shop import services as shop_services

        shop_services.sync_from_masters(reset_stock=False)
    except Exception:
        pass


def create_row(name: str, data: dict[str, Any]) -> dict[str, Any]:
    if name not in EDITABLE_MASTERS:
        raise ValueError("read_only")
    if not master_allows_create(name):
        raise ValueError("fixed_catalog")
    meta = get_master(name)
    assert meta
    col = get_db()[name]
    pk = meta["pk"]
    doc = {k: data[k] for k in meta["fields"] if k in data and k != pk}
    if pk not in data or not data.get(pk):
        doc[pk] = _next_id(col, pk)
    else:
        doc[pk] = int(data[pk]) if str(data[pk]).isdigit() else data[pk]
    _validate_master_row(name, doc)
    _check_master_duplicates(name, doc)
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
        doc.setdefault("sale_enabled", False)
        doc.setdefault("sale_percent", 25)
    if name == "dim_cliente":
        doc.setdefault("created_at", date.today().isoformat())
    doc.setdefault("active", True)
    col.insert_one(doc)
    if name == "dim_producto":
        from shared.commercial import record_product_terms
        record_product_terms(get_db(), product_id=int(doc[pk]), before=None, after=doc)
    log_audit("create", entity=name, entity_id=doc[pk], details={"pk": doc[pk]}, after=doc)
    _sync_shop_after_master_change(name)
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
    _validate_master_row(name, patch, partial=True)
    _check_master_duplicates(name, patch, exclude_key=key)
    if name == "dim_producto" and ("unit_price" in patch or "unit_cost" in patch or "sale_enabled" in patch):
        up = float(patch.get("unit_price", existing.get("unit_price") or 0))
        uc = float(patch.get("unit_cost", existing.get("unit_cost") or 0))
        patch["margin_pct"] = round(((up - uc) / up * 100) if up else 0, 2)
    col.update_one({pk: key}, {"$set": patch})
    if name == "dim_producto":
        from shared.commercial import record_product_terms
        record_product_terms(get_db(), product_id=int(key), before=existing, after={**existing, **patch})
    log_audit("update", entity=name, entity_id=key, details=patch, before=existing, after={**existing, **patch})
    _sync_shop_after_master_change(name)
    updated = col.find_one({pk: key}, {"_id": 0})
    return dict(updated) if updated else {}


def set_row_active(name: str, row_id: str, active: bool) -> dict[str, Any]:
    """Inhabilita/reactiva un maestro sin romper su historial ni sus relaciones."""
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
    col.update_one({pk: key}, {"$set": {"active": bool(active)}})
    action = "enable" if active else "disable"
    log_audit(
        action, entity=name, entity_id=key, details={"active": bool(active)},
        before=existing, after={**existing, "active": bool(active)},
    )
    _sync_shop_after_master_change(name)
    updated = col.find_one({pk: key}, {"_id": 0})
    return dict(updated) if updated else {pk: key, "active": bool(active)}


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
    existing = col.find_one({pk: key})
    if not existing:
        raise ValueError("not_found")
    _check_delete_refs(name, key)
    col.delete_one({pk: key})
    log_audit("delete", entity=name, entity_id=key, before=existing)
    _sync_shop_after_master_change(name)


def _check_delete_refs(name: str, key: Any) -> None:
    db = get_db()
    references: dict[str, list[tuple[str, str]]] = {
        "dim_region": [("dim_pais", "region_id"), ("vendors", "region_id"), ("fact_ventas", "region_id")],
        "dim_pais": [
            ("dim_cliente", "country_id"), ("vendors", "country_id"),
            ("purchase_requests", "country_id"), ("fact_ventas", "country_id"),
        ],
        "dim_categoria": [("dim_producto", "category_id"), ("fact_ventas", "category_id")],
        "dim_producto": [
            ("purchase_request_lines", "product_id"), ("fact_ventas", "product_id"),
        ],
        "dim_canal": [
            ("dim_cliente", "channel_id"), ("purchase_requests", "channel_id"),
            ("fact_ventas", "channel_id"),
        ],
        "dim_prioridad": [("fact_ventas", "priority_id")],
        "dim_cliente": [("fact_ventas", "client_id")],
    }
    for collection, field in references.get(name, []):
        if db[collection].count_documents({field: key}, limit=1):
            raise ValueError("has_history")


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
    try:
        from paquetes.tablero.queries import clear_query_cache

        clear_query_cache()
    except Exception:
        pass
    db = get_db()
    return {
        "sales_records": db["sales_records"].count_documents({}),
        "fact_ventas": db["fact_ventas"].count_documents({}),
        "dim_producto": db["dim_producto"].count_documents({}),
        "data_layer": "estrategico",
        "strategic_ready": db["fact_ventas"].count_documents({}, limit=1) > 0,
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
    try:
        from paquetes.tablero.queries import clear_query_cache

        clear_query_cache()
    except Exception:
        pass
    db = get_db()
    return {
        "message": "Dataset cargado y modelo reconstruido.",
        "sales_records": db["sales_records"].count_documents({}),
        "fact_ventas": db["fact_ventas"].count_documents({}),
    }


def get_elt_status() -> dict[str, Any]:
    from shared.data_layers import layers_overview
    from shared.mongo import mongo_topology

    db = get_db()
    pq = settings.data_parquet_dir / "sales_records.parquet"
    counts = {}
    for name in list(MASTER_TABLES.keys()) + ["sales_records", "fact_ventas", "purchase_requests", "audit_log"]:
        try:
            counts[name] = db[name].count_documents({})
        except Exception:
            counts[name] = 0
    layers = layers_overview()
    return {
        "mongo_db": settings.mongo_db,
        "mongo_uri": settings.mongo_uri.split("@")[-1],
        "parquet": str(pq),
        "parquet_exists": pq.exists(),
        "csv_source": str(settings.csv_source),
        "csv_exists": settings.csv_source.exists(),
        "counts": counts,
        "strategic_ready": layers.get("strategic_ready", False),
        "strategic_lagging": layers.get("strategic_lagging", False),
        "strategic_message": layers.get("message"),
        "last_build": layers.get("last_build"),
        "topology": mongo_topology(),
    }


def list_audit_log(
    *,
    limit: int = 100,
    offset: int = 0,
    role: str | None = None,
    entity: str | None = None,
    entity_id: str | int | None = None,
    email: str | None = None,
    action: str | None = None,
    module: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    col = get_db()["audit_log"]
    page_size = min(max(int(limit or 100), 1), 100)
    page_offset = max(int(offset or 0), 0)
    query: dict[str, Any] = {}
    role_filter = (role or "").strip()
    if role_filter:
        query["role"] = role_filter
    entity_filter = (entity or "").strip()
    if entity_filter:
        query["entity"] = entity_filter
    email_filter = (email or "").strip()
    if email_filter:
        query["email"] = {"$regex": re.escape(email_filter), "$options": "i"}
    action_filter = (action or "").strip()
    if action_filter:
        query["action"] = action_filter
    module_filter = (module or "").strip()
    if module_filter:
        query["module"] = module_filter
    if date_from or date_to:
        at_query: dict[str, str] = {}
        if date_from:
            at_query["$gte"] = f"{str(date_from)[:10]}T00:00:00"
        if date_to:
            at_query["$lte"] = f"{str(date_to)[:10]}T23:59:59.999999+00:00"
        query["at"] = at_query
    if entity_id is not None and str(entity_id).strip():
        raw = str(entity_id).strip()
        clauses: list[dict[str, Any]] = [{"entity_id": raw}]
        try:
            clauses.append({"entity_id": int(raw)})
        except (TypeError, ValueError):
            pass
        if len(clauses) == 1:
            query["entity_id"] = raw
        else:
            query["$or"] = clauses
    total = col.count_documents(query)
    rows = list(
        col.find(query, {"_id": 0})
        .sort("at", -1)
        .skip(page_offset)
        .limit(page_size)
    )
    roles = sorted({str(r).strip() for r in col.distinct("role") if r and str(r).strip()})
    actions = sorted({str(r).strip() for r in col.distinct("action") if r and str(r).strip()})
    modules = sorted({str(r).strip() for r in col.distinct("module") if r and str(r).strip()})
    return {
        "total": total,
        "limit": page_size,
        "offset": page_offset,
        "role": role_filter or None,
        "entity": entity_filter or None,
        "entity_id": str(entity_id).strip() if entity_id is not None and str(entity_id).strip() else None,
        "roles": roles,
        "actions": actions,
        "modules": modules,
        "entries": [json_safe(row) for row in rows],
    }


def list_audit_for_entity(
    entity: str,
    entity_id: str | int,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    return list_audit_log(
        limit=min(max(int(limit or 20), 1), 50),
        offset=0,
        entity=entity,
        entity_id=entity_id,
    )
