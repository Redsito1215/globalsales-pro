"""Servicios de compras — proveedores, inventario y órdenes de compra."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from shared.audit import log_audit
from shared.mongo import get_db
from shared.notifications import notify_roles
from shared.roles_registry import ADMIN_ROLE, VENDEDOR_ROLE
from shared.warehouse import DEFAULT_WAREHOUSE_NAME, warehouse_summary
from shared.inventory_ledger import record_movement, reorder_suggestion, stock_breakdown


def _enrich_vendor(row: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    if row.get("country_id") and not row.get("country"):
        pais = db["dim_pais"].find_one({"country_id": int(row["country_id"])}, {"_id": 0, "name": 1, "region_id": 1})
        if pais:
            row["country"] = pais.get("name")
            if not row.get("region_id"):
                row["region_id"] = pais.get("region_id")
    rid = row.get("region_id")
    if rid and not row.get("region_name"):
        reg = db["dim_region"].find_one({"region_id": int(rid)}, {"_id": 0, "name": 1})
        if reg:
            row["region_name"] = reg.get("name")
    return row


def _resolve_vendor_geo(data: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    from shared.checkout_countries import ensure_checkout_countries

    ensure_checkout_countries()
    country_id = data.get("country_id")
    region_id = data.get("region_id")
    country_name = (data.get("country") or "").strip() or None

    if country_id not in (None, ""):
        pais = db["dim_pais"].find_one({"country_id": int(country_id), "active": {"$ne": False}}, {"_id": 0})
        if not pais:
            raise ValueError("invalid_country")
        country_name = pais.get("name")
        region_id = pais.get("region_id")

    region_name = None
    if region_id not in (None, ""):
        reg = db["dim_region"].find_one({"region_id": int(region_id), "active": {"$ne": False}}, {"_id": 0, "name": 1})
        if not reg:
            raise ValueError("invalid_region")
        region_name = reg.get("name")

    return {
        "country": country_name,
        "country_id": int(country_id) if country_id not in (None, "") else None,
        "region_id": int(region_id) if region_id not in (None, "") else None,
        "region_name": region_name,
    }


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
    rows = list(db["vendors"].find(q, {"_id": 0}).sort("vendor_id", 1))
    return [_enrich_vendor(row) for row in rows]


def upsert_vendor(data: dict[str, Any], vendor_id: int | None = None) -> dict[str, Any]:
    db = get_db()
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name_required")
    geo = _resolve_vendor_geo(data)
    duplicate_query: dict[str, Any] = {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
    if vendor_id is not None:
        duplicate_query["vendor_id"] = {"$ne": int(vendor_id)}
    if db["vendors"].find_one(duplicate_query, {"vendor_id": 1}):
        raise ValueError("duplicate_vendor")
    email = (data.get("email") or "").strip().lower() or None
    if email:
        email_query: dict[str, Any] = {"email": email}
        if vendor_id is not None:
            email_query["vendor_id"] = {"$ne": int(vendor_id)}
        if db["vendors"].find_one(email_query, {"vendor_id": 1}):
            raise ValueError("duplicate_vendor_email")
    doc = {
        "name": name,
        "email": email,
        "country": geo.get("country"),
        "country_id": geo.get("country_id"),
        "region_id": geo.get("region_id"),
        "region_name": geo.get("region_name"),
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
    return _enrich_vendor(doc)


def set_vendor_active(vendor_id: int, active: bool, *, reason: str | None = None) -> dict[str, Any]:
    db = get_db()
    vid = int(vendor_id)
    current = db["vendors"].find_one({"vendor_id": vid})
    if not current:
        raise ValueError("not_found")
    clean_reason = (reason or "").strip()
    if not active and len(clean_reason) < 5:
        raise ValueError("reason_required")
    db["vendors"].update_one({"vendor_id": vid}, {"$set": {"active": bool(active)}})
    log_audit(
        "enable_vendor" if active else "disable_vendor",
        entity="vendors",
        entity_id=vid,
        details={"active": bool(active), "reason": clean_reason or None},
    )
    current["active"] = bool(active)
    current.pop("_id", None)
    return _enrich_vendor(current)


def delete_vendor(vendor_id: int) -> None:
    """Compatibilidad: nunca borra; exige usar inhabilitación explícita."""
    raise ValueError("use_disable")


# ── Inventario ──────────────────────────────────────────────────────────

def list_inventory(*, q: str | None = None, low_only: bool = False, threshold: int = 20, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    wh = warehouse_summary()
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
        inv_item = db["inventory_items"].find_one({"variant_id": v.get("variant_id")}, {"_id": 0, "inventory_item_id": 1})
        level = db["inventory_levels"].find_one({"inventory_item_id": (inv_item or {}).get("inventory_item_id")}, {"_id": 0}) if inv_item else {}
        committed = int((level or {}).get("committed") or 0)
        damaged_rows = db["inventory_scrapped"].find({"variant_id": v.get("variant_id")}, {"_id": 0, "quantity": 1})
        damaged = sum(int(x.get("quantity") or 0) for x in damaged_rows)
        open_pos = list(db["purchase_orders"].find({"status": {"$in": ["enviada", "parcial"]}}, {"_id": 0, "po_id": 1}))
        open_ids = [x.get("po_id") for x in open_pos]
        transit_lines = db["purchase_order_lines"].find({"po_id": {"$in": open_ids}, "variant_id": v.get("variant_id")}, {"_id": 0}) if open_ids else []
        in_transit = sum(max(int(x.get("quantity_ordered") or 0) - int(x.get("quantity_received") or 0), 0) for x in transit_lines)
        available = int(v.get("inventory_quantity") or 0)
        minimum = max(int(v.get("minimum_stock") or threshold), 0)
        target = max(int(v.get("reorder_target") or minimum * 2), minimum)
        balances = stock_breakdown(available=available, committed=committed, damaged=damaged, in_transit=in_transit)
        out.append(
            {
                "variant_id": v.get("variant_id"),
                "product_id": v.get("product_id"),
                "sku": sku,
                "title": title,
                "inventory_quantity": available,
                **balances,
                "minimum_stock": minimum,
                "reorder_target": target,
                "reorder_suggestion": reorder_suggestion(available=available, committed=committed, minimum=minimum, target=target),
                "price": float(v.get("price") or 0),
                "cost": float(v.get("cost") or 0),
                "vendor_id": (prod or {}).get("vendor_id"),
                "vendor": (vendor or {}).get("name") or "—",
                "warehouse": wh["name"],
                "warehouse_id": wh["warehouse_id"],
            }
        )
    return {"total": total if not term else len(out), "items": out, "threshold": threshold, "warehouse": wh}


def normalize_adjustment_reason(reason: str | None) -> str:
    clean = (reason or "").strip()
    if not clean:
        raise ValueError("reason_required")
    if len(clean) < 8:
        raise ValueError("reason_too_short")
    return clean[:240]


def set_stock(
    variant_id: int, available: int, *, reason: str | None = None,
    movement_type: str = "manual_adjustment", reference: str | None = None,
    actor_email: str | None = None,
) -> dict[str, Any]:
    from paquetes.shop.services import adjust_variant_stock

    db = get_db()
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        raise ValueError("invalid_variant")
    before = int(variant.get("inventory_quantity") or 0)
    clean_reason = normalize_adjustment_reason(reason)
    row = adjust_variant_stock(int(variant_id), int(available))
    after = int(row.get("inventory_quantity") or 0)
    record_movement(
        db, variant_id=int(variant_id), movement_type=movement_type, quantity=after - before,
        before=before, after=after, reason=clean_reason, actor_email=actor_email, reference=reference,
    )
    log_audit(
        "manual_stock_adjustment" if movement_type == "manual_adjustment" else movement_type,
        entity="product_variants", entity_id=int(variant_id),
        details={"before": before, "after": after, "reason": clean_reason, "reference": reference},
    )
    return row


def add_stock(
    variant_id: int, delta: int, *, reason: str | None = None,
    movement_type: str = "manual_adjustment", reference: str | None = None,
    actor_email: str | None = None,
) -> dict[str, Any]:
    db = get_db()
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)})
    if not variant:
        raise ValueError("invalid_variant")
    new_qty = max(int(variant.get("inventory_quantity") or 0) + int(delta), 0)
    return set_stock(
        int(variant_id), new_qty, reason=reason, movement_type=movement_type,
        reference=reference, actor_email=actor_email,
    )


def set_inventory_policy(variant_id: int, *, minimum: int, target: int) -> dict[str, Any]:
    if minimum < 0 or target < minimum:
        raise ValueError("invalid_inventory_policy")
    db = get_db()
    result = db["product_variants"].update_one(
        {"variant_id": int(variant_id)},
        {"$set": {"minimum_stock": int(minimum), "reorder_target": int(target)}},
    )
    if not result.matched_count:
        raise ValueError("invalid_variant")
    log_audit("inventory_policy", entity="product_variants", entity_id=variant_id, details={"minimum": minimum, "target": target})
    return {"variant_id": int(variant_id), "minimum_stock": int(minimum), "reorder_target": int(target)}


def list_kardex(variant_id: int, *, limit: int = 100) -> list[dict[str, Any]]:
    return list(get_db()["inventory_movements"].find(
        {"variant_id": int(variant_id)}, {"_id": 0}
    ).sort("movement_id", -1).limit(min(limit, 500)))


def register_physical_count(variant_id: int, *, counted: int, reason: str, actor_email: str | None = None) -> dict[str, Any]:
    if counted < 0:
        raise ValueError("invalid_stock")
    clean_reason = normalize_adjustment_reason(reason)
    db = get_db()
    variant = db["product_variants"].find_one({"variant_id": int(variant_id)}, {"_id": 0})
    if not variant:
        raise ValueError("invalid_variant")
    before = int(variant.get("inventory_quantity") or 0)
    counter = db["app_meta"].find_one_and_update(
        {"_id": "inventory_count_id"}, {"$inc": {"value": 1}}, upsert=True, return_document=True,
    )
    count_id = int((counter or {}).get("value") or 1)
    row = {
        "count_id": count_id, "variant_id": int(variant_id), "expected": before,
        "counted": int(counted), "difference": int(counted) - before,
        "reason": clean_reason, "actor_email": actor_email,
        "created_at": datetime.now(timezone.utc).isoformat(), "status": "applied",
    }
    db["inventory_counts"].insert_one(row)
    set_stock(
        int(variant_id), int(counted), reason=clean_reason, movement_type="physical_count",
        reference=f"COUNT-{count_id}", actor_email=actor_email,
    )
    row.pop("_id", None)
    return row


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
        "warehouse_id": warehouse_summary()["warehouse_id"],
        "warehouse": DEFAULT_WAREHOUSE_NAME,
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
        add_stock(
            int(line["variant_id"]), qty, reason=f"Recepción de orden de compra #{po_id}",
            movement_type="purchase_receipt", reference=f"PO-{po_id}",
        )
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


# ── Requisiciones internas (previo a OC a proveedor) ────────────────────

REQUISITION_STATUSES = frozenset({"borrador", "aprobada", "convertida", "cancelada"})


def list_purchase_requisitions(*, status: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    col = db["purchase_requisitions"]
    total = col.count_documents(query)
    rows = list(col.find(query, {"_id": 0}).sort("req_id", -1).skip(offset).limit(limit))
    for row in rows:
        row["lines"] = list(db["purchase_requisition_lines"].find({"req_id": row["req_id"]}, {"_id": 0}))
        if row.get("vendor_id"):
            vendor = db["vendors"].find_one({"vendor_id": row["vendor_id"]}, {"_id": 0, "name": 1})
            row["vendor_name"] = (vendor or {}).get("name")
    return {"total": total, "requisitions": rows}


def get_purchase_requisition(req_id: int) -> dict[str, Any] | None:
    db = get_db()
    row = db["purchase_requisitions"].find_one({"req_id": int(req_id)}, {"_id": 0})
    if not row:
        return None
    row["lines"] = list(db["purchase_requisition_lines"].find({"req_id": int(req_id)}, {"_id": 0}))
    if row.get("vendor_id"):
        vendor = db["vendors"].find_one({"vendor_id": row["vendor_id"]}, {"_id": 0})
        row["vendor"] = vendor
        row["vendor_name"] = (vendor or {}).get("name")
    return row


def create_purchase_requisition(data: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    vendor_id = int(data.get("vendor_id") or 0)
    vendor = db["vendors"].find_one({"vendor_id": vendor_id})
    if not vendor:
        raise ValueError("invalid_vendor")
    lines_in = data.get("lines") or []
    if not lines_in:
        raise ValueError("lines_required")

    req_id = _next_id(db["purchase_requisitions"], "req_id")
    doc = {
        "req_id": req_id,
        "vendor_id": vendor_id,
        "status": "borrador",
        "notes": (data.get("notes") or "").strip() or None,
        "created_at": date.today().isoformat(),
        "approved_at": None,
        "po_id": None,
    }
    db["purchase_requisitions"].insert_one(doc)

    line_docs = []
    lid = _next_id(db["purchase_requisition_lines"], "line_id")
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
                "req_id": req_id,
                "variant_id": vid,
                "product_id": int(variant.get("product_id") or 0),
                "sku": variant.get("sku"),
                "quantity": qty,
                "unit_cost": cost,
            }
        )
        lid += 1
    if line_docs:
        db["purchase_requisition_lines"].insert_many(line_docs)

    log_audit("create_requisition", entity="purchase_requisitions", entity_id=req_id)
    _notify_compras(
        f"Requisición #{req_id} creada",
        f"Requisición interna #{req_id} en borrador — requiere aprobación antes de generar OC.",
        meta={"req_id": req_id, "status": "borrador"},
    )
    return get_purchase_requisition(req_id) or {}


def approve_purchase_requisition(req_id: int) -> dict[str, Any]:
    db = get_db()
    row = db["purchase_requisitions"].find_one({"req_id": int(req_id)})
    if not row:
        raise ValueError("not_found")
    if row.get("status") != "borrador":
        raise ValueError("req_not_draft")
    db["purchase_requisitions"].update_one(
        {"req_id": int(req_id)},
        {"$set": {"status": "aprobada", "approved_at": date.today().isoformat()}},
    )
    log_audit("approve_requisition", entity="purchase_requisitions", entity_id=req_id)
    return get_purchase_requisition(req_id) or {}


def cancel_purchase_requisition(req_id: int) -> dict[str, Any]:
    db = get_db()
    row = db["purchase_requisitions"].find_one({"req_id": int(req_id)})
    if not row:
        raise ValueError("not_found")
    if row.get("status") in ("convertida", "cancelada"):
        raise ValueError("req_closed")
    db["purchase_requisitions"].update_one({"req_id": int(req_id)}, {"$set": {"status": "cancelada"}})
    log_audit("cancel_requisition", entity="purchase_requisitions", entity_id=req_id)
    return get_purchase_requisition(req_id) or {}


def convert_requisition_to_po(req_id: int) -> dict[str, Any]:
    """Genera una OC en borrador desde una requisición aprobada."""
    req = get_purchase_requisition(req_id)
    if not req:
        raise ValueError("not_found")
    if req.get("status") != "aprobada":
        raise ValueError("req_not_approved")
    lines = [
        {
            "variant_id": line["variant_id"],
            "quantity": line["quantity"],
            "unit_cost": line.get("unit_cost"),
        }
        for line in (req.get("lines") or [])
    ]
    po = create_purchase_order(
        {
            "vendor_id": req["vendor_id"],
            "notes": f"Desde requisición #{req_id}" + (f" — {req['notes']}" if req.get("notes") else ""),
            "lines": lines,
        }
    )
    db = get_db()
    db["purchase_requisitions"].update_one(
        {"req_id": int(req_id)},
        {"$set": {"status": "convertida", "po_id": po.get("po_id")}},
    )
    log_audit(
        "convert_requisition",
        entity="purchase_requisitions",
        entity_id=req_id,
        details={"po_id": po.get("po_id")},
    )
    return {"requisition": get_purchase_requisition(req_id), "purchase_order": po}


def list_scrapped_inventory(
    *,
    limit: int = 50,
    q: str | None = None,
) -> dict[str, Any]:
    """Merma por devoluciones — unidades dañadas que no vuelven a stock."""
    db = get_db()
    cap = min(max(int(limit or 50), 1), 200)
    rows = list(
        db["inventory_scrapped"]
        .find({}, {"_id": 0})
        .sort([("created_at", -1), ("request_id", -1)])
        .limit(cap * 3)
    )
    needle = (q or "").strip().lower()
    out: list[dict[str, Any]] = []
    for row in rows:
        vid = int(row.get("variant_id") or 0)
        variant = db["product_variants"].find_one({"variant_id": vid}, {"_id": 0, "sku": 1, "product_id": 1}) or {}
        pid = int(variant.get("product_id") or 0)
        product_name = ""
        if pid:
            prod = db["products"].find_one({"product_id": pid}, {"_id": 0, "title": 1, "name": 1})
            product_name = str((prod or {}).get("title") or (prod or {}).get("name") or "")
        enriched = {
            **row,
            "sku": variant.get("sku") or "",
            "product_name": product_name,
        }
        if needle:
            blob = f"{enriched.get('request_id')} {product_name} {variant.get('sku') or ''} {row.get('reason') or ''}".lower()
            if needle not in blob:
                continue
        out.append(enriched)
    items = out[:cap]
    total_units = sum(int(x.get("quantity") or 0) for x in items)
    return {"items": items, "total_units": total_units, "total_records": len(items)}
