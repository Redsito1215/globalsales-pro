# -*- coding: utf-8 -*-
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from werkzeug.security import generate_password_hash

from auth import users as user_store
from auth.validators import normalize_email, _validate_password_strength
from shared.mongo import get_db
from shared.notifications import notify_user

COLLECTION = "password_reset_tokens"
TOKEN_HOURS = 2


def _col():
    return get_db()[COLLECTION]


def create_reset_token(email: str) -> dict[str, Any] | None:
    email = normalize_email(email)
    user = user_store.find_by_email(email)
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    _col().delete_many({"email": email})
    _col().insert_one(
        {
            "email": email,
            "token": token,
            "expires_at": expires,
            "used": False,
            "created_at": datetime.now(timezone.utc),
        }
    )
    notify_user(
        recipient_email=email,
        subject="Recuperación de contraseña GLOBTRADE",
        body=(
            f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
            f"Código de recuperación: {token}\n\n"
            f"Válido por {TOKEN_HOURS} horas. En la pantalla de login usa «Restablecer contraseña» "
            f"y pega este código."
        ),
        category="seguridad",
        meta={"reset_token_hint": token[:8] + "…"},
    )
    return {"email": email, "token": token, "expires_at": expires.isoformat()}


def reset_password(token: str, new_password: str, password_confirm: str) -> dict[str, Any]:
    token = (token or "").strip()
    if not token:
        raise ValueError("token_required")
    pwd_err = _validate_password_strength(new_password)
    if pwd_err:
        raise ValueError("weak_password")
    if new_password != password_confirm:
        raise ValueError("password_mismatch")
    doc = _col().find_one({"token": token, "used": False})
    if not doc:
        raise ValueError("invalid_token")
    expires = doc.get("expires_at")
    if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValueError("expired_token")
    email = doc["email"]
    user = user_store.find_by_email(email)
    if not user:
        raise ValueError("invalid_token")
    get_db()["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": generate_password_hash(new_password)}},
    )
    _col().update_one({"token": token}, {"$set": {"used": True}})
    notify_user(
        recipient_email=email,
        subject="Contraseña actualizada",
        body="Tu contraseña fue restablecida correctamente. Si no fuiste tú, contacta soporte.",
        category="seguridad",
    )
    return user_store.public_user(user)
