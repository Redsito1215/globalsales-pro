# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from auth import roles_service
from shared.roles_registry import ADMIN_ROLE

COLLECTION = "users"


def _db():
    from shared.mongo import get_ops_db

    return get_ops_db()


def _col():
    return _db()[COLLECTION]


def ensure_indexes() -> None:
    _col().create_index([("email", ASCENDING)], unique=True, name="uniq_email")


def count_users() -> int:
    return _col().count_documents({})


def find_by_email(email: str) -> dict[str, Any] | None:
    return _col().find_one({"email": email, "active": True})


def find_by_id(user_id: str) -> dict[str, Any] | None:
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        oid = ObjectId(user_id)
    except InvalidId:
        return None
    return _col().find_one({"_id": oid, "active": True})


def public_user(doc: dict[str, Any]) -> dict[str, Any]:
    email = doc["email"]
    role = doc.get("role", "cliente")
    preferences = doc.get("preferences") or {}
    default_notifications = (
        {"orders": True, "inventory": False, "reports": False, "support": True}
        if role == "cliente"
        else {"orders": True, "inventory": True, "reports": True, "support": True}
    )
    return {
        "id": str(doc["_id"]),
        "email": email,
        "username": email,
        "name": doc.get("name", ""),
        "role": role,
        "avatar_url": doc.get("avatar_url"),
        "phone": doc.get("phone", ""),
        "job_title": doc.get("job_title", ""),
        "department": doc.get("department", ""),
        "country": doc.get("country", ""),
        "city": doc.get("city", ""),
        "language": preferences.get("language", "es"),
        "timezone": preferences.get("timezone", "America/Guayaquil"),
        "theme": preferences.get("theme", "light"),
        "notification_preferences": preferences.get("notifications") or default_notifications,
        "preferences_configured": bool(preferences),
        "permissions": roles_service.permissions_for_role(role),
        "role_label": (roles_service.get_role(role) or {}).get("label", role),
    }


def profile_suggestions(doc: dict[str, Any]) -> dict[str, str]:
    """Recupera datos de contacto fiables del pedido más reciente del cliente."""
    if doc.get("role") != "cliente":
        return {}
    db = _db()
    last = db["purchase_requests"].find_one(
        {"client_email": doc.get("email")},
        {"_id": 0, "client_phone": 1, "country_id": 1, "shipping_destination": 1},
        sort=[("request_id", -1)],
    ) or {}
    result: dict[str, str] = {}
    if last.get("client_phone"):
        result["phone"] = str(last["client_phone"])
    if last.get("country_id") is not None:
        country = db["dim_pais"].find_one(
            {"country_id": int(last["country_id"])}, {"_id": 0, "name": 1}
        ) or {}
        if country.get("name"):
            result["country"] = str(country["name"])
    destination = str(last.get("shipping_destination") or "").strip()
    if destination and "," not in destination and len(destination) <= 80:
        result["city"] = destination
    return result


def create_user(*, email: str, password: str, name: str, role: str = "cliente") -> dict[str, Any]:
    roles_service.ensure_roles_seed()
    role_doc = roles_service.get_role(role)
    if not role_doc or role_doc.get("active") is False:
        role = "cliente"
    doc = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "name": name,
        "role": role,
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        _col().insert_one(doc)
    except DuplicateKeyError:
        raise ValueError("duplicate_email") from None
    return doc


def verify_password(doc: dict[str, Any], password: str) -> bool:
    return check_password_hash(doc.get("password_hash", ""), password)


def count_active_admins() -> int:
    return _col().count_documents({"active": True, "role": ADMIN_ROLE})


def list_users(*, limit: int = 100, offset: int = 0, q: str | None = None) -> dict[str, Any]:
    query: dict[str, Any] = {"active": True}
    term = (q or "").strip()
    if term:
        rx = re.escape(term)
        query["$or"] = [
            {"email": {"$regex": rx, "$options": "i"}},
            {"name": {"$regex": rx, "$options": "i"}},
        ]
    total = _col().count_documents(query)
    rows = []
    for doc in _col().find(query).sort("email", 1).skip(offset).limit(limit):
        rows.append(public_user(doc))
    return {"total": total, "limit": limit, "offset": offset, "users": rows, "query": term or None}


def list_emails_by_roles(roles: list[str]) -> list[str]:
    role_set = {r for r in roles if r}
    if not role_set:
        return []
    emails: list[str] = []
    for doc in _col().find({"active": True, "role": {"$in": list(role_set)}}, {"email": 1}):
        email = (doc.get("email") or "").strip().lower()
        if email:
            emails.append(email)
    return emails


def update_user_role(user_id: str, role: str, *, actor_id: str | None = None) -> dict[str, Any]:
    roles_service.ensure_roles_seed()
    role_doc = roles_service.get_role(role)
    if not role_doc:
        raise ValueError("invalid_role")
    if role_doc.get("active") is False:
        raise ValueError("role_inactive")
    if not role_doc.get("assignable", True):
        raise ValueError("role_not_assignable")
    doc = find_by_id(user_id)
    if not doc:
        raise ValueError("not_found")
    if actor_id and str(doc["_id"]) == actor_id:
        raise ValueError("cannot_change_own_role")
    current_role = doc.get("role")
    if current_role == ADMIN_ROLE and role != ADMIN_ROLE and count_active_admins() <= 1:
        raise ValueError("cannot_change_last_admin")
    _col().update_one({"_id": doc["_id"]}, {"$set": {"role": role}})
    updated = find_by_id(user_id)
    return public_user(updated) if updated else {}


def deactivate_user(user_id: str, *, actor_id: str | None = None) -> dict[str, Any]:
    doc = find_by_id(user_id)
    if not doc:
        raise ValueError("not_found")
    if actor_id and str(doc["_id"]) == actor_id:
        raise ValueError("cannot_deactivate_self")
    if doc.get("role") == ADMIN_ROLE and count_active_admins() <= 1:
        raise ValueError("last_admin")
    pub = public_user(doc)
    _col().update_one({"_id": doc["_id"]}, {"$set": {"active": False}})
    return pub


def update_profile(
    user_id: str,
    *,
    name: str,
    email: str,
    current_password: str | None = None,
    new_password: str | None = None,
    profile_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc = find_by_id(user_id)
    if not doc:
        raise ValueError("not_found")

    email = email.strip().lower()
    name = name.strip()
    current = doc.get("email", "")
    email_changed = email != current
    password_change = bool(new_password)

    if email_changed or password_change:
        if not current_password or not verify_password(doc, current_password):
            raise ValueError("invalid_current_password")

    extra = profile_data or {}
    notifications = extra.get("notification_preferences") or {}
    updates: dict[str, Any] = {
        "name": name,
        "phone": str(extra.get("phone") or "").strip()[:30],
        "job_title": str(extra.get("job_title") or "").strip()[:80],
        "department": str(extra.get("department") or "").strip()[:80],
        "country": str(extra.get("country") or "").strip()[:80],
        "city": str(extra.get("city") or "").strip()[:80],
        "preferences": {
            "language": "en" if extra.get("language") == "en" else "es",
            "timezone": str(extra.get("timezone") or "America/Guayaquil")[:80],
            "theme": "dark" if extra.get("theme") == "dark" else "light",
            "notifications": {key: bool(notifications.get(key, True)) for key in ("orders", "inventory", "reports", "support")},
        },
    }
    if email_changed:
        if find_by_email(email):
            raise ValueError("duplicate_email")
        updates["email"] = email
    if password_change:
        updates["password_hash"] = generate_password_hash(new_password or "")

    _col().update_one({"_id": doc["_id"]}, {"$set": updates})
    updated = find_by_id(user_id)
    return public_user(updated) if updated else {}


def update_avatar(user_id: str, avatar_url: str) -> dict[str, Any]:
    """Actualiza solamente la foto del propietario del perfil."""
    doc = find_by_id(user_id)
    if not doc:
        raise ValueError("not_found")
    _col().update_one({"_id": doc["_id"]}, {"$set": {"avatar_url": avatar_url}})
    updated = find_by_id(user_id)
    return public_user(updated) if updated else {}
