"""Registro de auditoría para acciones administrativas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import has_request_context, session

from shared.mongo import get_db

_SENSITIVE_PARTS = ("password", "passwd", "secret", "token", "cvv", "cvc", "card_number", "pan")


def _safe_value(value: Any, key: str = "") -> Any:
    """Prepara valores auditables sin conservar credenciales ni datos de tarjeta."""
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_PARTS):
        return "[PROTEGIDO]"
    if isinstance(value, dict):
        return {str(k): _safe_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, key) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def audit_changes(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    """Devuelve únicamente los campos modificados, con valores anterior y nuevo."""
    old, new = before or {}, after or {}
    changes: dict[str, Any] = {}
    for key in sorted(set(old) | set(new)):
        if key == "_id" or old.get(key) == new.get(key):
            continue
        changes[key] = {
            "before": _safe_value(old.get(key), key),
            "after": _safe_value(new.get(key), key),
        }
    return changes


def _module_for(entity: str) -> str:
    name = (entity or "").lower()
    if any(part in name for part in ("invoice", "payment", "cash", "account", "credit_note")):
        return "contabilidad"
    if any(part in name for part in ("product", "producto", "stock", "inventory", "kardex")):
        return "inventario"
    if any(part in name for part in ("customer", "cliente", "discount", "commercial")):
        return "comercial"
    if any(part in name for part in ("order", "pedido", "purchase_request")):
        return "pedidos"
    if name in {"users", "roles", "permissions"}:
        return "seguridad"
    if name == "etl":
        return "datos"
    return "gestion"


def log_audit(
    action: str,
    *,
    entity: str,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    module: str | None = None,
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
        "module": module or _module_for(entity),
        "details": _safe_value(details or {}),
        "changes": audit_changes(before, after),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    get_db()["audit_log"].insert_one(doc)
