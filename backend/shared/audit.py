"""Registro de auditoría para acciones administrativas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import has_request_context, session

from shared.mongo import get_db


def log_audit(
    action: str,
    *,
    entity: str,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    user_id = email = role = None
    if has_request_context():
        user_id = session.get("user_id")
        email = session.get("email")
        role = session.get("role")
    doc = {
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "user_id": user_id,
        "email": email,
        "role": role,
        "details": details or {},
        "at": datetime.now(timezone.utc).isoformat(),
    }
    get_db()["audit_log"].insert_one(doc)
