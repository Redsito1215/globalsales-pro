"""Lotes de inventario, caducidad y trazabilidad FEFO."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_lot(*, variant_id: int, lot_code: str, quantity: int,
                 expiry_date: str | None = None, received_date: str | None = None,
                 po_id: int | None = None, actor_email: str | None = None) -> dict[str, Any]:
    code = str(lot_code or "").strip().upper()
    qty = int(quantity or 0)
    expiry = str(expiry_date or "").strip()[:10] or None
    if not code or qty < 1:
        raise ValueError("invalid_lot")
    if expiry:
        try:
            date.fromisoformat(expiry)
        except ValueError as exc:
            raise ValueError("invalid_expiry_date") from exc
    db = get_db()
    if not db["product_variants"].find_one({"variant_id": int(variant_id)}):
        raise ValueError("invalid_variant")
    key = {"variant_id": int(variant_id), "lot_code": code}
    existing = db["inventory_lots"].find_one(key, {"_id": 0})
    if existing and expiry and existing.get("expiry_date") not in (None, expiry):
        raise ValueError("lot_expiry_conflict")
    patch = {
        "expiry_date": expiry or (existing or {}).get("expiry_date"),
        "received_date": (received_date or date.today().isoformat())[:10],
        "updated_at": _now(), "po_id": po_id,
    }
    db["inventory_lots"].update_one(key, {"$set": patch, "$inc": {"quantity_available": qty, "quantity_received": qty}}, upsert=True)
    movement = {**key, "movement_type": "receipt", "quantity": qty, "po_id": po_id,
                "actor_email": actor_email, "created_at": _now()}
    db["lot_movements"].insert_one(movement)
    log_audit("lot_received", entity="inventory_lots", entity_id=f"{variant_id}:{code}", details=movement)
    return db["inventory_lots"].find_one(key, {"_id": 0}) or {}


def list_lots(*, variant_id: int | None = None, expiring_days: int | None = None,
              include_empty: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if variant_id:
        query["variant_id"] = int(variant_id)
    if not include_empty:
        query["quantity_available"] = {"$gt": 0}
    rows = list(get_db()["inventory_lots"].find(query, {"_id": 0}).sort([
        ("expiry_date", 1), ("received_date", 1), ("lot_code", 1)
    ]).limit(min(max(int(limit), 1), 500)))
    today = date.today()
    out = []
    for row in rows:
        expiry = row.get("expiry_date")
        days = None
        if expiry:
            try:
                days = (date.fromisoformat(str(expiry)[:10]) - today).days
            except ValueError:
                pass
        row["days_to_expiry"] = days
        row["expiry_status"] = "vencido" if days is not None and days < 0 else "por_vencer" if days is not None and days <= 30 else "vigente"
        if expiring_days is None or (days is not None and days <= int(expiring_days)):
            out.append(row)
    return out


def allocate_lots(*, variant_id: int, quantity: int, request_id: int | None = None) -> list[dict[str, Any]]:
    """Descuenta lotes por FEFO y deja trazabilidad; stock sin lotes sigue permitido."""
    remaining = int(quantity or 0)
    if remaining < 1:
        return []
    db = get_db()
    allocations = []
    for lot in db["inventory_lots"].find({"variant_id": int(variant_id), "quantity_available": {"$gt": 0}}).sort([
        ("expiry_date", 1), ("received_date", 1)
    ]):
        take = min(remaining, int(lot.get("quantity_available") or 0))
        if take < 1:
            continue
        db["inventory_lots"].update_one({"_id": lot["_id"]}, {"$inc": {"quantity_available": -take}, "$set": {"updated_at": _now()}})
        row = {"variant_id": int(variant_id), "lot_code": lot["lot_code"], "quantity": take,
               "request_id": request_id, "movement_type": "sale", "created_at": _now()}
        db["lot_movements"].insert_one(row)
        row.pop("_id", None)
        allocations.append(row)
        remaining -= take
        if remaining == 0:
            break
    return allocations


def trace_lot(lot_code: str) -> dict[str, Any]:
    code = str(lot_code or "").strip().upper()
    if not code:
        raise ValueError("invalid_lot")
    db = get_db()
    lots = list(db["inventory_lots"].find({"lot_code": code}, {"_id": 0}))
    movements = list(db["lot_movements"].find({"lot_code": code}, {"_id": 0}).sort("created_at", -1).limit(500))
    return {"lot_code": code, "lots": lots, "movements": movements,
            "received_units": sum(int(x.get("quantity_received") or 0) for x in lots),
            "available_units": sum(int(x.get("quantity_available") or 0) for x in lots)}


def restore_allocated_lots(*, allocations: list[dict[str, Any]], returned_lines: list[dict[str, Any]],
                           request_id: int, actor_email: str | None = None) -> list[dict[str, Any]]:
    """Reincorpora por lote únicamente unidades aptas devueltas."""
    db, restored = get_db(), []
    need = {int(x["variant_id"]): int(x["quantity"]) for x in returned_lines}
    for allocation in allocations or []:
        vid = int(allocation.get("variant_id") or 0)
        already = sum(int(x.get("quantity") or 0) for x in db["lot_movements"].find({
            "variant_id": vid, "lot_code": allocation.get("lot_code"),
            "request_id": int(request_id), "movement_type": "customer_return",
        }, {"quantity": 1}))
        remaining_allocation = max(int(allocation.get("quantity") or 0) - already, 0)
        qty = min(need.get(vid, 0), remaining_allocation)
        if qty < 1:
            continue
        key = {"variant_id": vid, "lot_code": allocation.get("lot_code")}
        db["inventory_lots"].update_one(key, {"$inc": {"quantity_available": qty}, "$set": {"updated_at": _now()}})
        movement = {**key, "movement_type": "customer_return", "quantity": qty,
                    "request_id": int(request_id), "actor_email": actor_email, "created_at": _now()}
        db["lot_movements"].insert_one(movement)
        movement.pop("_id", None)
        restored.append(movement)
        need[vid] -= qty
    return restored
