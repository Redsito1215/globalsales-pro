# -*- coding: utf-8 -*-
"""Libro de caja — entradas y salidas ligadas a solicitudes de venta."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.mongo import get_ops_db

COLLECTION = "cash_movements"
MOVEMENT_TYPES = frozenset({"payment_in", "refund_out", "adjustment"})


def _col():
    return get_ops_db()[COLLECTION]


def _next_id() -> int:
    row = _col().find_one({}, {"movement_id": 1}, sort=[("movement_id", -1)])
    return int(row["movement_id"]) + 1 if row and row.get("movement_id") else 1


def record_cash_movement(
    *,
    movement_type: str,
    amount: float,
    request_id: int,
    order_id: str | None = None,
    payment_method: str | None = None,
    actor_email: str | None = None,
    reference: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from shared.accounting import assert_period_open

    assert_period_open()
    kind = (movement_type or "").strip().lower()
    if kind not in MOVEMENT_TYPES:
        raise ValueError("invalid_cash_movement_type")
    value = round(float(amount or 0), 2)
    if value <= 0:
        raise ValueError("invalid_cash_amount")
    doc = {
        "movement_id": _next_id(),
        "movement_type": kind,
        "amount": value,
        "currency": "USD",
        "request_id": int(request_id),
        "order_id": (order_id or "").strip() or None,
        "payment_method": (payment_method or "").strip()[:40] or None,
        "actor_email": (actor_email or "").strip().lower() or None,
        "reference": (reference or "").strip()[:120] or None,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _col().insert_one(doc)
    doc.pop("_id", None)
    return doc


def list_movements_for_request(request_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
    return list(
        _col()
        .find({"request_id": int(request_id)}, {"_id": 0})
        .sort("movement_id", -1)
        .limit(min(limit, 100))
    )


def list_cash_movements(
    *,
    limit: int = 50,
    movement_type: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    """Listado global del libro de caja con resumen."""
    filt: dict[str, Any] = {}
    kind = (movement_type or "").strip().lower()
    if kind:
        filt["movement_type"] = kind
    cap = min(max(int(limit or 50), 1), 200)
    rows = list(_col().find(filt, {"_id": 0}).sort("movement_id", -1).limit(cap * 3))
    needle = (q or "").strip().lower()
    if needle:
        filtered: list[dict[str, Any]] = []
        for row in rows:
            haystack = " ".join(
                str(row.get(k) or "")
                for k in ("reference", "order_id", "actor_email", "payment_method", "movement_type")
            ).lower()
            if needle in haystack or needle == str(row.get("request_id")):
                filtered.append(row)
        rows = filtered
    rows = rows[:cap]
    total_in = sum(float(r.get("amount") or 0) for r in rows if r.get("movement_type") == "payment_in")
    total_out = sum(float(r.get("amount") or 0) for r in rows if r.get("movement_type") == "refund_out")
    return {
        "movements": rows,
        "summary": {
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "net": round(total_in - total_out, 2),
            "count": len(rows),
        },
    }
