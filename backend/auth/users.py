# -*- coding: utf-8 -*-
"""Persistencia de usuarios en MongoDB."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from config.settings import settings

COLLECTION = "users"
ROLES = frozenset({"analista", "administrador"})


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
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "name": doc.get("name", ""),
        "role": doc.get("role", "analista"),
    }


def create_user(*, email: str, password: str, name: str, role: str = "analista") -> dict[str, Any]:
    if role not in ROLES:
        role = "analista"
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
    doc.pop("password_hash", None)
    return doc


def verify_password(doc: dict[str, Any], password: str) -> bool:
    return check_password_hash(doc.get("password_hash", ""), password)
