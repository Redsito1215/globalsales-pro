# -*- coding: utf-8 -*-
"""Notificaciones in-app / correo simulado para demo académica."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.mongo import get_db

COLLECTION = "user_notifications"


def _col():
    return get_db()[COLLECTION]


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


def list_for_email(email: str, *, limit: int = 50, unread_only: bool = False) -> dict[str, Any]:
    email = (email or "").strip().lower()
    query: dict[str, Any] = {"recipient_email": email}
    if unread_only:
        query["read"] = False
    total = _col().count_documents({"recipient_email": email})
    unread = _col().count_documents({"recipient_email": email, "read": False})
    rows = list(
        _col().find(query, {"_id": 0})
        .sort("notification_id", -1)
        .limit(min(limit, 200))
    )
    return {"total": total, "unread": unread, "notifications": rows}


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


def status_message(status: str, request_id: int) -> tuple[str, str]:
    labels = {
        "pendiente": "Pendiente",
        "en_revision": "En revisión",
        "aprobada": "Aprobada",
        "convertida": "Convertida en venta",
        "rechazada": "Rechazada",
        "cancelada": "Cancelada por el cliente",
    }
    label = labels.get(status, status)
    subject = f"Solicitud #{request_id} — {label}"
    body = (
        f"Tu solicitud de compra #{request_id} cambió a estado: {label}.\n"
        f"Revisa Mis pedidos o Notificaciones en GLOBTRADE."
    )
    return subject, body
