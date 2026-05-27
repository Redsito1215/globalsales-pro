# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify, session


def _unauthorized(message: str = "Debes iniciar sesión para realizar esta acción."):
    return jsonify({"status": "error", "message": message, "code": "auth_required"}), 401


def _forbidden(message: str = "No tienes permisos para esta acción."):
    return jsonify({"status": "error", "message": message, "code": "forbidden"}), 403


def current_user_id() -> str | None:
    return session.get("user_id")


def current_user_role() -> str | None:
    return session.get("role")


def login_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return _unauthorized()
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return _unauthorized()
        if session.get("role") != "administrador":
            return _forbidden("Solo administradores pueden ejecutar esta operación.")
        return fn(*args, **kwargs)

    return wrapper
