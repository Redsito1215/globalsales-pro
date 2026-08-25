"""Kardex y cálculos de existencias para una única bodega."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def stock_breakdown(*, available: int = 0, committed: int = 0, damaged: int = 0, in_transit: int = 0) -> dict[str, int]:
    values = {"available": available, "committed": committed, "damaged": damaged, "in_transit": in_transit}
    clean = {key: max(int(value or 0), 0) for key, value in values.items()}
    clean["physical"] = clean["available"] + clean["committed"] + clean["damaged"]
    return clean


def reorder_suggestion(*, available: int, committed: int, minimum: int, target: int | None = None) -> int:
    usable = max(int(available or 0) - int(committed or 0), 0)
    floor = max(int(minimum or 0), 0)
    desired = max(int(target if target is not None else floor * 2), floor)
    return max(desired - usable, 0) if usable <= floor else 0


def record_movement(
    db: Any, *, variant_id: int, movement_type: str, quantity: int,
    before: int, after: int, reason: str, actor_email: str | None = None,
    reference: str | None = None, metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inserta un asiento de kardex. Los asientos nunca se modifican ni eliminan."""
    counter = db["app_meta"].find_one_and_update(
        {"_id": "inventory_movement_id"}, {"$inc": {"value": 1}}, upsert=True, return_document=True,
    )
    movement_id = int((counter or {}).get("value") or 1)
    doc = {
        "movement_id": movement_id, "variant_id": int(variant_id),
        "movement_type": str(movement_type), "quantity": int(quantity),
        "before": int(before), "after": int(after), "reason": str(reason).strip(),
        "reference": reference, "actor_email": actor_email,
        "created_at": datetime.now(timezone.utc).isoformat(), "metadata": metadata or {},
    }
    db["inventory_movements"].insert_one(doc)
    doc.pop("_id", None)
    return doc

