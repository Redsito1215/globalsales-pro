# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from collections import defaultdict

from flask import Blueprint, jsonify, request, session

from auth import users as user_store
from auth.decorators import login_required
from auth.validators import normalize_email, validate_login, validate_register

auth_bp = Blueprint("auth", __name__)

# Limitación básica de intentos de login (seguridad)
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 8
_WINDOW_SEC = 900


def _client_key() -> str:
    return request.remote_addr or "unknown"


def _check_rate_limit() -> str | None:
    key = _client_key()
    now = time.time()
    attempts = [t for t in _LOGIN_ATTEMPTS[key] if now - t < _WINDOW_SEC]
    _LOGIN_ATTEMPTS[key] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        return "Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo."
    return None


def _record_failed_login():
    _LOGIN_ATTEMPTS[_client_key()].append(time.time())


def _clear_login_attempts():
    _LOGIN_ATTEMPTS.pop(_client_key(), None)


def _set_session(user: dict) -> None:
    pub = user_store.public_user(user)
    session.clear()
    session.permanent = True
    session["user_id"] = pub["id"]
    session["email"] = pub["email"]
    session["name"] = pub["name"]
    session["role"] = pub["role"]


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")
    password_confirm = data.get("password_confirm", data.get("password2", ""))
    name = (data.get("name", "") or "").strip()

    errors = validate_register(email, password, password_confirm, name)
    if errors:
        return jsonify({"status": "error", "message": "Datos inválidos.", "errors": errors}), 400

    role = "administrador" if user_store.count_users() == 0 else "analista"

    try:
        doc = user_store.create_user(email=email, password=password, name=name, role=role)
    except ValueError as e:
        if str(e) == "duplicate_email":
            return jsonify(
                {
                    "status": "error",
                    "message": "Ya existe una cuenta con ese correo.",
                    "errors": {"email": "Este correo ya está registrado."},
                }
            ), 409
        raise

    full = user_store.find_by_email(email)
    if not full:
        return jsonify({"status": "error", "message": "No se pudo crear la cuenta."}), 500

    _set_session(full)
    return jsonify(
        {
            "status": "ok",
            "message": "Cuenta creada correctamente.",
            "user": user_store.public_user(full),
        }
    ), 201


@auth_bp.post("/login")
def login():
    rate_msg = _check_rate_limit()
    if rate_msg:
        return jsonify({"status": "error", "message": rate_msg}), 429

    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")

    errors = validate_login(email, password)
    if errors:
        return jsonify({"status": "error", "message": "Datos inválidos.", "errors": errors}), 400

    doc = user_store.find_by_email(email)
    if not doc or not user_store.verify_password(doc, password):
        _record_failed_login()
        return jsonify(
            {
                "status": "error",
                "message": "Correo o contraseña incorrectos.",
                "errors": {"email": "Credenciales no válidas."},
            }
        ), 401

    _clear_login_attempts()
    _set_session(doc)
    return jsonify(
        {
            "status": "ok",
            "message": "Sesión iniciada.",
            "user": user_store.public_user(doc),
        }
    )


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok", "message": "Sesión cerrada."})


@auth_bp.get("/me")
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"status": "ok", "authenticated": False, "user": None})

    doc = user_store.find_by_id(uid)
    if not doc:
        session.clear()
        return jsonify({"status": "ok", "authenticated": False, "user": None})

    return jsonify(
        {
            "status": "ok",
            "authenticated": True,
            "user": user_store.public_user(doc),
        }
    )


@auth_bp.get("/session")
@login_required
def session_info():
    return jsonify(
        {
            "status": "ok",
            "user": {
                "id": session.get("user_id"),
                "email": session.get("email"),
                "name": session.get("name"),
                "role": session.get("role"),
            },
        }
    )
