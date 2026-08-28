# -*- coding: utf-8 -*-
"""Notificaciones in-app (bandeja del usuario)."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from shared.mongo import get_collection

COLLECTION = "user_notifications"


def _col():
    return get_collection(COLLECTION)


def _next_id() -> int:
    row = _col().find_one({}, {"notification_id": 1}, sort=[("notification_id", -1)])
    return int(row["notification_id"]) + 1 if row and row.get("notification_id") else 1


def notify_user(
    *,
    recipient_email: str,
    subject: str,
    body: str,
    category: str = "sistema",
    request_id: int | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    email = (recipient_email or "").strip().lower()
    if not email:
        return {}
    doc = {
        "notification_id": _next_id(),
        "recipient_email": email,
        "subject": subject,
        "body": body,
        "category": category,
        "request_id": request_id,
        "meta": meta or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _col().insert_one(doc)
    doc.pop("_id", None)
    return doc


def list_for_email(
    email: str, *, limit: int = 50, unread_only: bool = False,
    category: str | None = None, q: str | None = None, offset: int = 0,
) -> dict[str, Any]:
    email = (email or "").strip().lower()
    query: dict[str, Any] = {"recipient_email": email}
    if unread_only:
        query["read"] = False
    clean_category = (category or "").strip().lower()
    if clean_category:
        query["category"] = clean_category
    term = (q or "").strip()
    if term:
        pattern = re.escape(term[:120])
        query["$or"] = [
            {"subject": {"$regex": pattern, "$options": "i"}},
            {"body": {"$regex": pattern, "$options": "i"}},
        ]
    total = _col().count_documents(query)
    unread = _col().count_documents({"recipient_email": email, "read": False})
    rows = list(
        _col().find(query, {"_id": 0})
        .sort("notification_id", -1)
        .skip(max(int(offset or 0), 0))
        .limit(min(limit, 200))
    )
    category_counts = {
        str(row.get("_id") or "sistema"): int(row.get("count") or 0)
        for row in _col().aggregate([
            {"$match": {"recipient_email": email}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        ])
    }
    return {"total": total, "unread": unread, "notifications": rows, "category_counts": category_counts}


def pulse_for_email(email: str, *, after_id: int = 0) -> dict[str, Any]:
    """Devuelve contador y notificaciones nuevas desde after_id (para polling en vivo)."""
    email = (email or "").strip().lower()
    if not email:
        return {"unread": 0, "latest_id": 0, "new": []}
    unread = _col().count_documents({"recipient_email": email, "read": False})
    latest_row = _col().find_one(
        {"recipient_email": email},
        {"notification_id": 1},
        sort=[("notification_id", -1)],
    )
    latest_id = int(latest_row["notification_id"]) if latest_row else 0
    after = max(int(after_id or 0), 0)
    new_rows: list[dict[str, Any]] = []
    if after > 0 and latest_id > after:
        new_rows = list(
            _col().find(
                {"recipient_email": email, "notification_id": {"$gt": after}},
                {"_id": 0},
            )
            .sort("notification_id", 1)
            .limit(20)
        )
    return {"unread": unread, "latest_id": latest_id, "new": new_rows}


def mark_read(notification_id: int, email: str) -> bool:
    email = (email or "").strip().lower()
    res = _col().update_one(
        {"notification_id": int(notification_id), "recipient_email": email},
        {"$set": {"read": True}},
    )
    return res.modified_count > 0


def mark_all_read(email: str) -> int:
    email = (email or "").strip().lower()
    res = _col().update_many({"recipient_email": email, "read": False}, {"$set": {"read": True}})
    return res.modified_count


def mark_category_read(email: str, category: str) -> int:
    email = (email or "").strip().lower()
    clean = (category or "").strip().lower()
    if not clean:
        raise ValueError("category_required")
    res = _col().update_many(
        {"recipient_email": email, "category": clean, "read": False}, {"$set": {"read": True}}
    )
    return res.modified_count


def status_message(status: str, request_id: int) -> tuple[str, str]:
    labels = {
        "pendiente": "Pendiente",
        "en_revision": "En revisión",
        "aprobada": "Aprobada",
        "convertida": "Convertida en venta",
        "enviada": "Enviada",
        "entregada": "Entregada",
        "devuelta": "Devuelta",
        "rechazada": "Rechazada",
        "cancelada": "Cancelada por el cliente",
    }
    label = labels.get(status, status)
    subject = f"Solicitud #{request_id} — {label}"
    if status == "enviada":
        body = (
            f"Tu solicitud #{request_id} fue enviada.\n"
            f"Puedes revisar el seguimiento en Mis pedidos."
        )
    elif status == "entregada":
        body = (
            f"Tu solicitud #{request_id} fue marcada como entregada.\n"
            f"Gracias por comprar en Altavia Trade."
        )
    elif status == "devuelta":
        body = (
            f"Tu solicitud #{request_id} fue marcada como devolución.\n"
            f"El inventario fue repuesto. Revisa Mis pedidos en Altavia Trade."
        )
    else:
        body = (
            f"Tu solicitud de compra #{request_id} cambió a estado: {label}.\n"
            f"Revisa Mis pedidos o Notificaciones en Altavia Trade."
        )
    return subject, body


def notify_roles(
    *,
    roles: tuple[str, ...] | list[str],
    subject: str,
    body: str,
    category: str = "sistema",
    request_id: int | None = None,
    meta: dict[str, Any] | None = None,
    exclude_email: str | None = None,
) -> int:
    """Notifica a todos los usuarios activos con alguno de los roles indicados."""
    from auth.users import list_emails_by_roles

    emails = list_emails_by_roles(list(roles))
    skip = (exclude_email or "").strip().lower()
    sent = 0
    for email in emails:
        if skip and email == skip:
            continue
        doc = notify_user(
            recipient_email=email,
            subject=subject,
            body=body,
            category=category,
            request_id=request_id,
            meta=meta,
        )
        if doc:
            sent += 1
    return sent
