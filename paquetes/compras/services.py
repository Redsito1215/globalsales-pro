"""Servicios de compras — proveedores, inventario y órdenes de compra."""
from __future__ import annotations

from datetime import date
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db
from shared.notifications import notify_roles
from shared.roles_registry import ADMIN_ROLE, VENDEDOR_ROLE


def _next_id(col, pk: str) -> int:
    row = col.find_one({}, {pk: 1, "_id": 0}, sort=[(pk, -1)])
    return int(row[pk]) + 1 if row and row.get(pk) is not None else 1


def _notify_compras(subject: str, body: str, *, po_id: int | None = None, meta: dict[str, Any] | None = None) -> None:
    notify_roles(
        roles=(ADMIN_ROLE, VENDEDOR_ROLE),
        subject=subject,
        body=body,
        category="compras",
        meta={"po_id": po_id, **(meta or {})} if po_id is not None else meta,
    )


# ── Proveedores ─────────────────────────────────────────────────────────

def list_vendors(*, active_only: bool = False) -> list[dict[str, Any]]:
    db = get_db()
    q: dict[str, Any] = {}
    if active_only:
        q["active"] = True
    return list(db["vendors"].find(q, {"_id": 0}).sort("vendor_id", 1))


def upsert_vendor(data: dict[str, Any], vendor_id: int | None = None) -> dict[str, Any]:
    db = get_db()
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name_required")
    doc = {
        "name": name,
        "email": (data.get("email") or "").strip() or None,
        "country": (data.get("country") or "").strip() or None,
        "phone": (data.get("phone") or "").strip() or None,
        "active": bool(data.get("active", True)),
    }
    if vendor_id is None:
        vid = _next_id(db["vendors"], "vendor_id")
        doc["vendor_id"] = vid
        db["vendors"].insert_one(doc)
        log_audit("create_vendor", entity="vendors", entity_id=vid, details=doc)
    else:
        vid = int(vendor_id)
        exists = db["vendors"].find_one({"vendor_id": vid})
        if not exists:
            raise ValueError("not_found")
        db["vendors"].update_one({"vendor_id": vid}, {"$set": doc})
        doc["vendor_id"] = vid
        log_audit("update_vendor", entity="vendors", entity_id=vid, details=doc)
    return doc


def delete_vendor(vendor_id: int) -> None:
    db = get_db()
    res = db["vendors"].delete_one({"vendor_id": int(vendor_id)})
    if not res.deleted_count:
        raise ValueError("not_found")
    log_audit("delete_vendor", entity="vendors", entity_id=vendor_id)


# ── Inventario ──────────────────────────────────────────────────────────

def list_inventory(*, q: str | None = None, low_only: bool = False, threshold: int = 20, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if low_only:
        query["inventory_quantity"] = {"$lte": int(threshold)}
    total = db["product_variants"].count_documents(query)
    rows = list(
        db["product_variants"]
        .find(query, {"_id": 0})
        .sort("inventory_quantity", 1)
        .skip(offset)
        .limit(limit)
    )
    term = (q or "").strip().lower()
    out = []
    for v in rows:
        prod = db["products"].find_one({"product_id": v.get("product_id")}, {"_id": 0, "title": 1, "vendor_id": 1})
        vendor = None
        if prod and prod.get("vendor_id"):
            vendor = db["vendors"].find_one({"vendor_id": prod["vendor_id"]}, {"_id": 0, "name": 1})
        title = (prod or {}).get("title") or f"Producto {v.get('product_id')}"
        sku = v.get("sku") or ""
        if term and term not in title.lower() and term not in sku.lower() and term not in str(v.get("variant_id")):
            continue
        out.append(
            {
                "variant_id": v.get("variant_id"),
                "product_id": v.get("product_id"),
                "sku": sku,
                "title": title,
                "inventory_quantity": int(v.get("inventory_quantity") or 0),
                "price": float(v.get("price") or 0),
                "cost": float(v.get("cost") or 0),
                "vendor_id": (prod or {}).get("vendor_id"),
                "vendor": (vendor or {}).get("name") or "—",
            }
        )
    return {"total": total if not term else len(out), "items": out, "threshold": threshold}


def set_stock(variant_id: int, available: int) -> dict[str, Any]:
    from paquetes.shop.services import adjust_variant_stock

    return adjust_variant_stock(int(variant_id), int(available))


def add_stock(variant_id: int, delta: int) -> dict[str, Any]:
    db = get_db()
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        raise ValueError("invalid_variant")
    new_qty = max(int(variant.get("inventory_quantity") or 0) + int(delta), 0)
    return set_stock(int(variant_id), new_qty)


# ── Órdenes de compra ───────────────────────────────────────────────────

PO_STATUSES = frozenset({"borrador", "enviada", "parcial", "recibida", "cancelada"})


def list_purchase_orders(*, status: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    col = db["purchase_orders"]
    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).sort("po_id", -1).skip(offset).limit(limit))
    for row in rows:
        row["lines"] = list(db["purchase_order_lines"].find({"po_id": row["po_id"]}, {"_id": 0}))
        vendor = db["vendors"].find_one({"vendor_id": row.get("vendor_id")}, {"_id": 0, "name": 1})
        row["vendor_name"] = (vendor or {}).get("name")
    return {"total": total, "orders": rows}


def get_purchase_order(po_id: int) -> dict[str, Any] | None:
    db = get_db()
    row = db["purchase_orders"].find_one({"po_id": int(po_id)}, {"_id": 0})
    if not row:
        return None
    row["lines"] = list(db["purchase_order_lines"].find({"po_id": int(po_id)}, {"_id": 0}))
    vendor = db["vendors"].find_one({"vendor_id": row.get("vendor_id")}, {"_id": 0})
    row["vendor"] = vendor
    return row


def create_purchase_order(data: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    vendor_id = int(data.get("vendor_id") or 0)
    vendor = db["vendors"].find_one({"vendor_id": vendor_id})
    if not vendor:
        raise ValueError("invalid_vendor")
    lines_in = data.get("lines") or []
    if not lines_in:
        raise ValueError("lines_required")

    send_now = bool(data.get("send")) or str(data.get("status") or "").strip().lower() == "enviada"
    initial_status = "enviada" if send_now else "borrador"

    po_id = _next_id(db["purchase_orders"], "po_id")
    po = {
        "po_id": po_id,
        "vendor_id": vendor_id,
        "status": initial_status,
        "notes": (data.get("notes") or "").strip() or None,
        "created_at": date.today().isoformat(),
        "sent_at": date.today().isoformat() if initial_status == "enviada" else None,
        "received_at": None,
    }
    db["purchase_orders"].insert_one(po)

    line_docs = []
    lid = _next_id(db["purchase_order_lines"], "line_id")
    for item in lines_in:
        vid = int(item.get("variant_id") or 0)
        qty = int(item.get("quantity") or 0)
        if vid < 1 or qty < 1:
            raise ValueError("invalid_line")
        variant = db["product_variants"].find_one({"variant_id": vid})
        if not variant:
            raise ValueError("invalid_variant")
        cost = float(item.get("unit_cost") if item.get("unit_cost") is not None else (variant.get("cost") or 0))
        line_docs.append(
            {
                "line_id": lid,
                "po_id": po_id,
                "variant_id": vid,
                "product_id": int(variant.get("product_id") or 0),
                "sku": variant.get("sku"),
                "quantity_ordered": qty,
                "quantity_received": 0,
                "unit_cost": cost,
            }
        )
        lid += 1
    if line_docs:
        db["purchase_order_lines"].insert_many(line_docs)

    log_audit("create_po", entity="purchase_orders", entity_id=po_id, details={"status": initial_status})
    if initial_status == "enviada":
        vendor_name = vendor.get("name") or f"#{vendor_id}"
        _notify_compras(
            f"OC #{po_id} enviada",
            f"Orden de compra #{po_id} creada y enviada a {vendor_name}.",
            po_id=po_id,
            meta={"status": "enviada", "vendor_id": vendor_id},
        )
    return get_purchase_order(po_id) or po


def send_purchase_order(po_id: int) -> dict[str, Any]:
    """Pasa una OC de borrador a enviada."""
    db = get_db()
    po = db["purchase_orders"].find_one({"po_id": int(po_id)})
    if not po:
        raise ValueError("not_found")
    if po.get("status") != "borrador":
        raise ValueError("po_not_draft")
    lines = list(db["purchase_order_lines"].find({"po_id": int(po_id)}))
    if not lines:
        raise ValueError("no_lines")
    db["purchase_orders"].update_one(
        {"po_id": int(po_id)},
        {"$set": {"status": "enviada", "sent_at": date.today().isoformat()}},
    )
    log_audit("send_po", entity="purchase_orders", entity_id=po_id)
    vendor = db["vendors"].find_one({"vendor_id": po.get("vendor_id")}, {"_id": 0, "name": 1})
    vendor_name = (vendor or {}).get("name") or f"#{po.get('vendor_id')}"
    _notify_compras(
        f"OC #{po_id} enviada",
        f"Orden de compra #{po_id} enviada a {vendor_name}. Lista para recepción de mercancía.",
        po_id=po_id,
        meta={"status": "enviada", "vendor_id": po.get("vendor_id")},
    )
    return get_purchase_order(po_id) or {}


def receive_purchase_order(po_id: int, *, receipts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Recibe OC (completa o parcial) y sube stock."""
    db = get_db()
    po = db["purchase_orders"].find_one({"po_id": int(po_id)})
    if not po:
        raise ValueError("not_found")
    if po.get("status") == "borrador":
        raise ValueError("po_not_sent")
    if po.get("status") in ("recibida", "cancelada"):
        raise ValueError("po_closed")

    lines = list(db["purchase_order_lines"].find({"po_id": int(po_id)}))
    if not lines:
        raise ValueError("no_lines")

    receipt_map: dict[int, int] = {}
    if receipts:
        for r in receipts:
            receipt_map[int(r.get("line_id") or 0)] = int(r.get("quantity") or 0)
    else:
        for line in lines:
            pending = int(line.get("quantity_ordered") or 0) - int(line.get("quantity_received") or 0)
            if pending > 0:
                receipt_map[int(line["line_id"])] = pending

    received_any = False
    for line in lines:
        lid = int(line["line_id"])
        qty = receipt_map.get(lid, 0)
        if qty < 1:
            continue
        pending = int(line.get("quantity_ordered") or 0) - int(line.get("quantity_received") or 0)
        qty = min(qty, pending)
        if qty < 1:
            continue
        add_stock(int(line["variant_id"]), qty)
        db["purchase_order_lines"].update_one(
            {"line_id": lid},
            {"$inc": {"quantity_received": qty}},
        )
        received_any = True

    if not received_any:
        raise ValueError("nothing_to_receive")

    # Recalcular estado
    lines = list(db["purchase_order_lines"].find({"po_id": int(po_id)}))
    all_done = all(
        int(l.get("quantity_received") or 0) >= int(l.get("quantity_ordered") or 0) for l in lines
    )
    any_recv = any(int(l.get("quantity_received") or 0) > 0 for l in lines)
    status = "recibida" if all_done else ("parcial" if any_recv else po.get("status"))
    patch: dict[str, Any] = {"status": status}
    if status == "recibida":
        patch["received_at"] = date.today().isoformat()
    db["purchase_orders"].update_one({"po_id": int(po_id)}, {"$set": patch})
    log_audit("receive_po", entity="purchase_orders", entity_id=po_id, details={"status": status})
    _notify_compras(
        f"OC #{po_id} — recepción ({status})",
        f"Se registró recepción en la orden de compra #{po_id}. Estado actual: {status}.",
        po_id=po_id,
        meta={"status": status},
    )
    return get_purchase_order(po_id) or {}


def cancel_purchase_order(po_id: int) -> dict[str, Any]:
    db = get_db()
    po = db["purchase_orders"].find_one({"po_id": int(po_id)})
    if not po:
        raise ValueError("not_found")
    if po.get("status") == "recibida":
        raise ValueError("po_closed")
    if po.get("status") == "cancelada":
        raise ValueError("po_closed")
    db["purchase_orders"].update_one({"po_id": int(po_id)}, {"$set": {"status": "cancelada"}})
    log_audit("cancel_po", entity="purchase_orders", entity_id=po_id)
    _notify_compras(
        f"OC #{po_id} cancelada",
        f"La orden de compra #{po_id} fue cancelada.",
        po_id=po_id,
        meta={"status": "cancelada"},
    )
    return get_purchase_order(po_id) or {}
