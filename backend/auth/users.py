# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from auth import roles_service
from config.settings import settings

COLLECTION = "users"


def _db():
    return MongoClient(settings.mongo_uri)[settings.mongo_db]


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
    return {
        "id": str(doc["_id"]),
        "email": email,
        "username": email,
        "name": doc.get("name", ""),
        "role": role,
    }


def create_user(*, email: str, password: str, name: str, role: str = "cliente") -> dict[str, Any]:
    roles_service.ensure_roles_seed()
    if not roles_service.role_exists(role):
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


def list_users(*, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    query = {"active": True}
    total = _col().count_documents(query)
    rows = []
    for doc in _col().find(query).sort("email", 1).skip(offset).limit(limit):
        rows.append(public_user(doc))
    return {"total": total, "limit": limit, "offset": offset, "users": rows}


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


def update_user_role(user_id: str, role: str) -> dict[str, Any]:
    roles_service.ensure_roles_seed()
    role_doc = roles_service.get_role(role)
    if not role_doc:
        raise ValueError("invalid_role")
    if not role_doc.get("assignable", True):
        raise ValueError("role_not_assignable")
    doc = find_by_id(user_id)
    if not doc:
        raise ValueError("not_found")
    _col().update_one({"_id": doc["_id"]}, {"$set": {"role": role}})
    updated = find_by_id(user_id)
    return public_user(updated) if updated else {}


def update_profile(
    user_id: str,
    *,
    name: str,
    email: str,
    current_password: str | None = None,
    new_password: str | None = None,
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

    updates: dict[str, Any] = {"name": name}
    if email_changed:
        if find_by_email(email):
            raise ValueError("duplicate_email")
        updates["email"] = email
    if password_change:
        updates["password_hash"] = generate_password_hash(new_password or "")

    if updates.get("email") == current and updates.get("name") == doc.get("name") and not password_change:
        return public_user(doc)

    _col().update_one({"_id": doc["_id"]}, {"$set": updates})
    updated = find_by_id(user_id)
    return public_user(updated) if updated else {}
