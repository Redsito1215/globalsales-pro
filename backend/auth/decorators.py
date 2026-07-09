# -*- coding: utf-8 -*-
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify, session

from auth import roles_service


def login_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(
                {"status": "error", "message": "Debes iniciar sesión.", "code": "auth_required"}
            ), 401
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(
                {"status": "error", "message": "Debes iniciar sesión.", "code": "auth_required"}
            ), 401
        if session.get("role") != "administrador":
            return jsonify(
                {
                    "status": "error",
                    "message": "Solo administradores pueden hacer esto.",
                    "code": "forbidden",
                }
            ), 403
        return fn(*args, **kwargs)

    return wrapper


def permission_required(permission: str):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return jsonify(
                    {"status": "error", "message": "Debes iniciar sesión.", "code": "auth_required"}
                ), 401
            role = session.get("role")
            if role == "administrador" or roles_service.has_permission(role, permission):
                return fn(*args, **kwargs)
            return jsonify(
                {
                    "status": "error",
                    "message": "No tienes permiso para esta acción.",
                    "code": "forbidden",
                }
            ), 403

        return wrapper

    return decorator
