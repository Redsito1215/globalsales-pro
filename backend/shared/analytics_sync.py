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


def _ensure_tiempo(db, fecha_id: str | None, cache: dict | None = None) -> int | None:
    if not fecha_id:
        return None
    key = str(fecha_id)[:10]
    if cache is not None and ("t", key) in cache:
        return cache[("t", key)]
    existing = db["dim_tiempo"].find_one({"fecha_id": key}, {"tiempo_id": 1, "_id": 0})
    if existing:
        val = int(existing["tiempo_id"])
    else:
        try:
            dt = datetime.fromisoformat(key)
        except ValueError:
            val = None
        else:
            last = db["dim_tiempo"].find_one({}, {"tiempo_id": 1, "_id": 0}, sort=[("tiempo_id", -1)])
            tid = int(last["tiempo_id"]) + 1 if last and last.get("tiempo_id") is not None else 1
            q = (dt.month - 1) // 3 + 1
            db["dim_tiempo"].insert_one(
                {
                    "tiempo_id": tid,
                    "fecha_id": key,
                    "anio": dt.year,
                    "mes": dt.month,
                    "trimestre": q,
                }
            )
            val = tid
    if cache is not None:
        cache[("t", key)] = val
    return val


def _lookup_region_id(db, name: str | None, cache: dict | None = None) -> int | None:
    if not name:
        return None
    if cache is not None and ("r", name) in cache:
        return cache[("r", name)]
    doc = db["dim_region"].find_one({"name": name}, {"region_id": 1, "_id": 0})
    val = int(doc["region_id"]) if doc else None
    if cache is not None:
        cache[("r", name)] = val
    return val


def _lookup_country_id(db, name: str | None, cache: dict | None = None) -> int | None:
    if not name:
        return None
    if cache is not None and ("c", name) in cache:
        return cache[("c", name)]
    doc = db["dim_pais"].find_one({"name": name}, {"country_id": 1, "_id": 0})
    val = int(doc["country_id"]) if doc else None
    if cache is not None:
        cache[("c", name)] = val
    return val


def _lookup_category_id(db, name: str | None, cache: dict | None = None) -> int | None:
    if not name:
        return None
    if cache is not None and ("cat", name) in cache:
        return cache[("cat", name)]
    doc = db["dim_categoria"].find_one({"name": name}, {"category_id": 1, "_id": 0})
    val = int(doc["category_id"]) if doc else None
    if cache is not None:
        cache[("cat", name)] = val
    return val


def _lookup_channel_id(db, name: str | None, cache: dict | None = None) -> int | None:
    if not name:
        return None
    if cache is not None and ("ch", name) in cache:
        return cache[("ch", name)]
    doc = db["dim_canal"].find_one({"name": name}, {"channel_id": 1, "_id": 0})
    val = int(doc["channel_id"]) if doc else None
    if cache is not None:
        cache[("ch", name)] = val
    return val


def _lookup_priority_id(db, code_or_name: str | None, cache: dict | None = None) -> int | None:
    if not code_or_name:
        return None
    if cache is not None and ("p", code_or_name) in cache:
        return cache[("p", code_or_name)]
    doc = db["dim_prioridad"].find_one(
        {"$or": [{"code": code_or_name}, {"name": code_or_name}]},
        {"priority_id": 1, "_id": 0},
    )
    val = int(doc["priority_id"]) if doc else None
    if cache is not None:
        cache[("p", code_or_name)] = val
    return val


def _lookup_client_id(db, country: str | None, channel: str | None, cache: dict | None = None) -> int | None:
    c_id = _lookup_country_id(db, country, cache)
    ch_id = _lookup_channel_id(db, channel, cache)
    if c_id is None or ch_id is None:
        return None
    key = ("cl", c_id, ch_id)
    if cache is not None and key in cache:
        return cache[key]
    doc = db["dim_cliente"].find_one(
        {"country_id": c_id, "channel_id": ch_id},
        {"client_id": 1, "_id": 0},
    )
    val = int(doc["client_id"]) if doc else None
    if cache is not None:
        cache[key] = val
    return val


def _row_to_fact(db, row: dict[str, Any], venta_id: int, cache: dict | None = None) -> dict[str, Any]:
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
        "tiempo_id": _ensure_tiempo(db, fecha_id, cache),
        "fecha_id": fecha_id,
        "region_id": _lookup_region_id(db, row.get("region"), cache),
        "country_id": _lookup_country_id(db, row.get("country"), cache),
        "category_id": _lookup_category_id(db, row.get("item_type"), cache),
        "product_id": int(row.get("product_id") or 0),
        "product_name": str(row.get("product_name") or ""),
        "channel_id": _lookup_channel_id(db, row.get("sales_channel"), cache),
        "priority_id": _lookup_priority_id(db, row.get("order_priority"), cache),
        "client_id": _lookup_client_id(db, row.get("country"), row.get("sales_channel"), cache),
        "units_sold": u,
        "unit_price": up,
        "unit_cost": uc,
        "total_revenue": rev,
        "total_cost": cost,
        "total_profit": profit,
        "line_revenue": round(u * up, 2),
        "line_cost": round(u * uc, 2),
        "line_profit": round(u * (up - uc), 2),
        "discount_code": str(row.get("discount_code") or ""),
        "discount_alloc": float(row.get("discount_alloc") or 0),
    }


def _month_key_from_fecha(fecha_id: str | None) -> tuple[int, int] | None:
    raw = str(fecha_id or "")[:10]
    if len(raw) < 7 or raw[4] != "-":
        return None
    try:
        year = int(raw[:4])
        month = int(raw[5:7])
    except ValueError:
        return None
    if month < 1 or month > 12:
        return None
    return year, month


def rebuild_monthly_kpis_for_month(year: int, month: int) -> int:
    """Recalcula KPIs mensuales de un mes desde fact_ventas (idempotente)."""
    db = get_db()
    prefix = f"{int(year):04d}-{int(month):02d}"
    db["monthly_kpis"].delete_many({"year": int(year), "month": int(month)})

    rows = list(
        db["fact_ventas"].find(
            {"fecha_id": {"$regex": f"^{prefix}"}},
            {
                "_id": 0,
                "fecha_id": 1,
                "region_id": 1,
                "category_id": 1,
                "units_sold": 1,
                "total_revenue": 1,
                "total_cost": 1,
                "total_profit": 1,
            },
        )
    )
    if not rows:
        return 0

    region_names: dict[int, str] = {}
    category_names: dict[int, str] = {}
    buckets: dict[tuple[str, str], dict[str, float | int]] = {}

    for row in rows:
        rid = row.get("region_id")
        cid = row.get("category_id")
        region = "—"
        item_type = "—"
        if rid is not None:
            if int(rid) not in region_names:
                doc = db["dim_region"].find_one({"region_id": int(rid)}, {"name": 1, "_id": 0})
                region_names[int(rid)] = str((doc or {}).get("name") or "—")
            region = region_names[int(rid)]
        if cid is not None:
            if int(cid) not in category_names:
                doc = db["dim_categoria"].find_one({"category_id": int(cid)}, {"name": 1, "_id": 0})
                category_names[int(cid)] = str((doc or {}).get("name") or "—")
            item_type = category_names[int(cid)]

        key = (region, item_type)
        bucket = buckets.setdefault(
            key,
            {
                "total_orders": 0,
                "total_units": 0,
                "total_revenue": 0.0,
                "total_cost": 0.0,
                "total_profit": 0.0,
            },
        )
        bucket["total_orders"] = int(bucket["total_orders"]) + 1
        bucket["total_units"] = int(bucket["total_units"]) + int(row.get("units_sold") or 0)
        bucket["total_revenue"] = float(bucket["total_revenue"]) + float(row.get("total_revenue") or 0)
        bucket["total_cost"] = float(bucket["total_cost"]) + float(row.get("total_cost") or 0)
        bucket["total_profit"] = float(bucket["total_profit"]) + float(
            row.get("total_profit")
            if row.get("total_profit") is not None
            else float(row.get("total_revenue") or 0) - float(row.get("total_cost") or 0)
        )

    last = db["monthly_kpis"].find_one({}, {"kpi_id": 1, "_id": 0}, sort=[("kpi_id", -1)])
    next_id = int(last["kpi_id"]) + 1 if last and last.get("kpi_id") is not None else 1
    docs: list[dict[str, Any]] = []
    for (region, item_type), agg in buckets.items():
        rev = round(float(agg["total_revenue"]), 2)
        prof = round(float(agg["total_profit"]), 2)
        docs.append(
            {
                "kpi_id": next_id,
                "year": int(year),
                "month": int(month),
                "region": region,
                "item_type": item_type,
                "total_orders": int(agg["total_orders"]),
                "total_units": int(agg["total_units"]),
                "total_revenue": rev,
                "total_cost": round(float(agg["total_cost"]), 2),
                "total_profit": prof,
                "avg_margin_pct": round((prof / rev * 100) if rev else 0.0, 2),
            }
        )
        next_id += 1
    if docs:
        db["monthly_kpis"].insert_many(docs)
    return len(docs)


def refresh_monthly_kpis_for_order(order_id: str | int) -> list[tuple[int, int]]:
    """Recalcula KPIs de los meses tocados por un order_id."""
    db = get_db()
    oid = str(order_id)
    rows = list(db["fact_ventas"].find({"order_id": oid}, {"fecha_id": 1, "_id": 0}))
    if not rows:
        try:
            rows = list(db["fact_ventas"].find({"order_id": int(oid)}, {"fecha_id": 1, "_id": 0}))
        except (TypeError, ValueError):
            rows = []
    months: set[tuple[int, int]] = set()
    for row in rows:
        key = _month_key_from_fecha(row.get("fecha_id"))
        if key:
            months.add(key)
    for year, month in sorted(months):
        rebuild_monthly_kpis_for_month(year, month)
    return sorted(months)


def sync_order_to_fact(order_id: str | int, *, force: bool = False) -> dict[str, Any]:
    """Append (o re-sincroniza con force) hechos de un order_id desde sales_records → fact_ventas."""
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

    if force:
        db["fact_ventas"].delete_many({"order_id": oid})
        try:
            db["fact_ventas"].delete_many({"order_id": int(oid)})
        except (TypeError, ValueError):
            pass
    else:
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
    kpi_months: list[tuple[int, int]] = []
    try:
        kpi_months = refresh_monthly_kpis_for_order(oid)
    except Exception:
        pass
    return {
        "order_id": oid,
        "synced": len(hechos),
        "skipped": False,
        "analytics_stale": False,
        "fact_ventas_count": db["fact_ventas"].estimated_document_count(),
        "kpi_months_refreshed": [{"year": y, "month": m} for y, m in kpi_months],
        "message": f"Sincronizados {len(hechos)} hecho(s) a fact_ventas.",
    }


def sync_orders_bulk(order_ids, *, limit: int | None = None) -> dict[str, Any]:
    """Sincroniza una lista de order_ids (landing) → fact_ventas con caché de dimensiones."""
    db = get_db()
    cache: dict = {}
    next_id = _next_venta_id(db)
    synced = 0
    facts_inserted = 0
    done: set[str] = set()
    for raw in order_ids:
        if limit and synced >= limit:
            break
        oid = str(raw)
        if oid in done:
            continue
        done.add(oid)
        if db["fact_ventas"].count_documents({"order_id": oid}, limit=1):
            continue
        try:
            if db["fact_ventas"].count_documents({"order_id": int(oid)}, limit=1):
                continue
        except (TypeError, ValueError):
            pass
        rows = list(db["sales_records"].find({"order_id": oid}, {"_id": 0}))
        if not rows:
            try:
                rows = list(db["sales_records"].find({"order_id": int(oid)}, {"_id": 0}))
            except (TypeError, ValueError):
                pass
        if not rows:
            continue
        hechos = [_row_to_fact(db, r, next_id + i, cache) for i, r in enumerate(rows)]
        if hechos:
            db["fact_ventas"].insert_many(hechos)
            next_id += len(hechos)
            facts_inserted += len(hechos)
            synced += 1

    if facts_inserted:
        try:
            from paquetes.tablero.queries import clear_query_cache

            clear_query_cache()
        except Exception:
            pass
        set_strategic_lag(False)
    return {"synced_orders": synced, "facts_inserted": facts_inserted}


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
    try:
        recent = list(
            db["sales_records"]
            .find({}, {"order_id": 1, "_id": 0})
            .sort([("order_date", -1), ("_id", -1)])
            .limit(max(limit * 3, 50))
            .max_time_ms(8000)
        )
    except Exception as exc:
        return {
            "orders_synced": [],
            "facts_inserted": 0,
            "errors": [f"sales_records:{type(exc).__name__}"],
            "strategic_lagging": True,
        }
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
