# -*- coding: utf-8 -*-
"""Sync incremental landing (sales_records) → estratégico (fact_ventas)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.mongo import get_db


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _next_venta_id(db) -> int:
    row = db["fact_ventas"].find_one({}, {"venta_id": 1, "_id": 0}, sort=[("venta_id", -1)])
    return int(row["venta_id"]) + 1 if row and row.get("venta_id") is not None else 1


def _ensure_tiempo(db, fecha_id: str | None) -> int | None:
    if not fecha_id:
        return None
    existing = db["dim_tiempo"].find_one({"fecha_id": fecha_id}, {"tiempo_id": 1, "_id": 0})
    if existing:
        return int(existing["tiempo_id"])
    try:
        dt = datetime.fromisoformat(str(fecha_id)[:10])
    except ValueError:
        return None
    last = db["dim_tiempo"].find_one({}, {"tiempo_id": 1, "_id": 0}, sort=[("tiempo_id", -1)])
    tid = int(last["tiempo_id"]) + 1 if last and last.get("tiempo_id") is not None else 1
    q = (dt.month - 1) // 3 + 1
    db["dim_tiempo"].insert_one(
        {
            "tiempo_id": tid,
            "fecha_id": fecha_id[:10],
            "anio": dt.year,
            "mes": dt.month,
            "trimestre": q,
        }
    )
    return tid


def _lookup_region_id(db, name: str | None) -> int | None:
    if not name:
        return None
    doc = db["dim_region"].find_one({"name": name}, {"region_id": 1, "_id": 0})
    return int(doc["region_id"]) if doc else None


def _lookup_country_id(db, name: str | None) -> int | None:
    if not name:
        return None
    doc = db["dim_pais"].find_one({"name": name}, {"country_id": 1, "_id": 0})
    return int(doc["country_id"]) if doc else None


def _lookup_category_id(db, name: str | None) -> int | None:
    if not name:
        return None
    doc = db["dim_categoria"].find_one({"name": name}, {"category_id": 1, "_id": 0})
    return int(doc["category_id"]) if doc else None


def _lookup_channel_id(db, name: str | None) -> int | None:
    if not name:
        return None
    doc = db["dim_canal"].find_one({"name": name}, {"channel_id": 1, "_id": 0})
    return int(doc["channel_id"]) if doc else None


def _lookup_priority_id(db, code_or_name: str | None) -> int | None:
    if not code_or_name:
        return None
    doc = db["dim_prioridad"].find_one(
        {"$or": [{"code": code_or_name}, {"name": code_or_name}]},
        {"priority_id": 1, "_id": 0},
    )
    return int(doc["priority_id"]) if doc else None


def _lookup_client_id(db, country: str | None, channel: str | None) -> int | None:
    c_id = _lookup_country_id(db, country)
    ch_id = _lookup_channel_id(db, channel)
    if c_id is None or ch_id is None:
        return None
    doc = db["dim_cliente"].find_one(
        {"country_id": c_id, "channel_id": ch_id},
        {"client_id": 1, "_id": 0},
    )
    return int(doc["client_id"]) if doc else None


def _row_to_fact(db, row: dict[str, Any], venta_id: int) -> dict[str, Any]:
    fecha_raw = row.get("order_date")
    fecha_id = str(fecha_raw)[:10] if fecha_raw else None
    u = int(row.get("units_sold") or 0)
    up = float(row.get("unit_price") or 0)
    uc = float(row.get("unit_cost") or 0)
    rev = float(row.get("total_revenue") or round(u * up, 2))
    cost = float(row.get("total_cost") or round(u * uc, 2))
    profit = float(row.get("total_profit") if row.get("total_profit") is not None else rev - cost)
    return {
        "venta_id": venta_id,
        "order_id": str(row.get("order_id")),
        "tiempo_id": _ensure_tiempo(db, fecha_id),
        "fecha_id": fecha_id,
        "region_id": _lookup_region_id(db, row.get("region")),
        "country_id": _lookup_country_id(db, row.get("country")),
        "category_id": _lookup_category_id(db, row.get("item_type")),
        "channel_id": _lookup_channel_id(db, row.get("sales_channel")),
        "priority_id": _lookup_priority_id(db, row.get("order_priority")),
        "client_id": _lookup_client_id(db, row.get("country"), row.get("sales_channel")),
        "units_sold": u,
        "unit_price": up,
        "unit_cost": uc,
        "total_revenue": rev,
        "total_cost": cost,
        "total_profit": profit,
        "line_revenue": round(u * up, 2),
        "line_cost": round(u * uc, 2),
        "line_profit": round(u * (up - uc), 2),
    }


def sync_order_to_fact(order_id: str | int) -> dict[str, Any]:
    """Append hechos de un order_id desde sales_records → fact_ventas."""
    db = get_db()
    oid = str(order_id)
    rows = list(db["sales_records"].find({"order_id": oid}, {"_id": 0}))
    if not rows:
        # order_id a veces numérico en landing
        try:
            rows = list(db["sales_records"].find({"order_id": int(oid)}, {"_id": 0}))
        except (TypeError, ValueError):
            pass
    if not rows:
        raise ValueError("order_not_in_landing")

    # Idempotencia: si ya hay hechos, no duplicar
    existing = db["fact_ventas"].count_documents({"order_id": oid}, limit=1)
    if not existing:
        try:
            existing = db["fact_ventas"].count_documents({"order_id": int(oid)}, limit=1)
        except (TypeError, ValueError):
            existing = 0
    if existing:
        return {
            "order_id": oid,
            "synced": 0,
            "skipped": True,
            "analytics_stale": False,
            "message": "Ya estaba en fact_ventas.",
        }

    next_id = _next_venta_id(db)
    hechos = []
    for i, row in enumerate(rows):
        hechos.append(_row_to_fact(db, row, next_id + i))
    if hechos:
        db["fact_ventas"].insert_many(hechos)

    try:
        from paquetes.tablero.queries import clear_query_cache

        clear_query_cache()
    except Exception:
        pass

    set_strategic_lag(False)
    return {
        "order_id": oid,
        "synced": len(hechos),
        "skipped": False,
        "analytics_stale": False,
        "fact_ventas_count": db["fact_ventas"].estimated_document_count(),
        "message": f"Sincronizados {len(hechos)} hecho(s) a fact_ventas.",
    }


def set_strategic_lag(lagging: bool, *, detail: str | None = None) -> None:
    db = get_db()
    db["app_meta"].update_one(
        {"_id": "strategic_sync"},
        {
            "$set": {
                "strategic_lagging": bool(lagging),
                "detail": detail,
                "updated_at": _utc_now_iso(),
            }
        },
        upsert=True,
    )


def get_strategic_lag() -> dict[str, Any]:
    db = get_db()
    doc = db["app_meta"].find_one({"_id": "strategic_sync"}) or {}
    lagging = bool(doc.get("strategic_lagging"))
    # Heurística: order_ids recientes en landing ausentes en fact
    missing = 0
    sample: list[str] = []
    try:
        recent = list(
            db["sales_records"]
            .find({}, {"order_id": 1, "_id": 0})
            .sort([("order_date", -1), ("_id", -1)])
            .limit(40)
        )
        seen: set[str] = set()
        for r in recent:
            oid = str(r.get("order_id"))
            if not oid or oid in seen:
                continue
            seen.add(oid)
            if db["fact_ventas"].count_documents({"order_id": oid}, limit=1) == 0:
                try:
                    if db["fact_ventas"].count_documents({"order_id": int(oid)}, limit=1) == 0:
                        missing += 1
                        if len(sample) < 5:
                            sample.append(oid)
                except (TypeError, ValueError):
                    missing += 1
                    if len(sample) < 5:
                        sample.append(oid)
        if missing:
            lagging = True
        elif doc.get("strategic_lagging") and not missing:
            lagging = False
            set_strategic_lag(False)
    except Exception:
        pass
    return {
        "strategic_lagging": lagging,
        "missing_sample": sample,
        "missing_approx": missing,
        "detail": doc.get("detail"),
        "updated_at": doc.get("updated_at"),
    }


def sync_stale_orders(*, limit: int = 50) -> dict[str, Any]:
    """Sincroniza order_ids recientes de landing que faltan en fact."""
    db = get_db()
    recent = list(
        db["sales_records"]
        .find({}, {"order_id": 1, "_id": 0})
        .sort([("order_date", -1), ("_id", -1)])
        .limit(max(limit * 3, 50))
    )
    synced_total = 0
    orders: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for r in recent:
        oid = str(r.get("order_id") or "")
        if not oid or oid in seen:
            continue
        seen.add(oid)
        in_fact = db["fact_ventas"].count_documents({"order_id": oid}, limit=1)
        if not in_fact:
            try:
                in_fact = db["fact_ventas"].count_documents({"order_id": int(oid)}, limit=1)
            except (TypeError, ValueError):
                in_fact = 0
        if in_fact:
            continue
        try:
            res = sync_order_to_fact(oid)
            synced_total += int(res.get("synced") or 0)
            orders.append(oid)
        except Exception as e:
            errors.append(f"{oid}:{e}")
        if len(orders) >= limit:
            break
    lag = get_strategic_lag()
    if not lag.get("strategic_lagging"):
        set_strategic_lag(False)
    return {
        "orders_synced": orders,
        "facts_inserted": synced_total,
        "errors": errors,
        "strategic_lagging": lag.get("strategic_lagging"),
        "analytics_stale": bool(lag.get("strategic_lagging")),
    }
