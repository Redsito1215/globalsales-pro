# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from collections import defaultdict

from flask import Blueprint, jsonify, request, session

from auth import roles_service, users as user_store
from auth.decorators import admin_required, login_required
from auth.validators import normalize_email, validate_login, validate_profile_update, validate_register
from shared.audit import log_audit
from shared.roles_registry import ADMIN_ROLE, DEFAULT_REGISTER_ROLE

auth_bp = Blueprint("auth", __name__)

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
        return "Demasiados intentos fallidos. Espera unos minutos."
    return None


def _set_session(user: dict) -> None:
    pub = user_store.public_user(user)
    session.clear()
    session.permanent = True
    session["user_id"] = pub["id"]
    session["email"] = pub["email"]
    session["name"] = pub["name"]
    session["role"] = pub["role"]


def _access_for_session() -> dict:
    role = session.get("role")
    payload = roles_service.access_payload(role)
    payload["role"] = role
    payload["authenticated"] = bool(session.get("user_id"))
    return payload


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

    role = ADMIN_ROLE if user_store.count_users() == 0 else DEFAULT_REGISTER_ROLE

    try:
        user_store.create_user(email=email, password=password, name=name, role=role)
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
    log_audit("register", entity="users", entity_id=email, details={"role": role})
    return jsonify(
        {
            "status": "ok",
            "message": "Cuenta creada correctamente.",
            "user": user_store.public_user(full),
            "access": _access_for_session(),
        }
    ), 201


@auth_bp.post("/login")
def login():
    rate_msg = _check_rate_limit()
    if rate_msg:
        return jsonify({"status": "error", "message": rate_msg}), 429

    data = request.get_json(silent=True) or {}
    raw = data.get("email") or data.get("username") or ""
    email = normalize_email(raw)
    password = data.get("password", "")

    errors = validate_login(email, password)
    if errors:
        return jsonify({"status": "error", "message": "Datos inválidos.", "errors": errors}), 400

    doc = user_store.find_by_email(email)
    if not doc or not user_store.verify_password(doc, password):
        _LOGIN_ATTEMPTS[_client_key()].append(time.time())
        return jsonify(
            {"status": "error", "message": "Correo o contraseña incorrectos."},
        ), 401

    _LOGIN_ATTEMPTS.pop(_client_key(), None)
    _set_session(doc)
    return jsonify(
        {
            "status": "ok",
            "message": "Sesión iniciada.",
            "user": user_store.public_user(doc),
            "access": _access_for_session(),
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
        return jsonify(
            {
                "status": "ok",
                "authenticated": False,
                "user": None,
                "access": roles_service.access_payload(None),
            }
        )

    doc = user_store.find_by_id(uid)
    if not doc:
        session.clear()
        return jsonify(
            {
                "status": "ok",
                "authenticated": False,
                "user": None,
                "access": roles_service.access_payload(None),
            }
        )

    return jsonify(
        {
            "status": "ok",
            "authenticated": True,
            "user": user_store.public_user(doc),
            "access": _access_for_session(),
        }
    )


@auth_bp.get("/access")
def access():
    return jsonify({"status": "ok", **_access_for_session()})


@auth_bp.patch("/profile")
@login_required
def profile_update():
    body = request.get_json(silent=True) or {}
    uid = session.get("user_id")
    doc = user_store.find_by_id(uid)
    if not doc:
        session.clear()
        return jsonify({"status": "error", "message": "Sesión no válida."}), 401

    name = (body.get("name") or "").strip()
    email = normalize_email(body.get("email", doc.get("email", "")))
    current_password = body.get("current_password") or ""
    new_password = body.get("new_password") or ""
    password_confirm = body.get("password_confirm", body.get("password2", ""))
    email_changed = email != doc.get("email", "")
    password_change = bool(new_password)

    errors = validate_profile_update(
        name=name,
        email=email,
        current_password=current_password,
        new_password=new_password,
        password_confirm=password_confirm,
        email_changed=email_changed,
        password_change=password_change,
    )
    if errors:
        return jsonify({"status": "error", "message": "Datos inválidos.", "errors": errors}), 400

    try:
        user = user_store.update_profile(
            uid,
            name=name,
            email=email,
            current_password=current_password or None,
            new_password=new_password or None,
        )
    except ValueError as e:
        return _profile_error(e)

    full = user_store.find_by_id(uid)
    if full:
        _set_session(full)
    log_audit(
        "update_profile",
        entity="users",
        entity_id=uid,
        details={"email_changed": email_changed, "password_change": password_change},
    )
    return jsonify(
        {
            "status": "ok",
            "message": "Perfil actualizado.",
            "user": user,
            "access": _access_for_session(),
        }
    )


@auth_bp.get("/roles")
@admin_required
def roles_list():
    return jsonify({"status": "ok", "roles": roles_service.list_roles()})


@auth_bp.post("/roles")
@admin_required
def roles_create():
    body = request.get_json(silent=True) or {}
    try:
        role = roles_service.create_role(body)
        log_audit("create_role", entity="app_roles", entity_id=role["slug"])
        return jsonify({"status": "ok", "role": role}), 201
    except ValueError as e:
        return _roles_error(e)


@auth_bp.put("/roles/<slug>")
@admin_required
def roles_update(slug: str):
    body = request.get_json(silent=True) or {}
    try:
        role = roles_service.update_role(slug, body)
        log_audit("update_role", entity="app_roles", entity_id=slug, details=body)
        return jsonify({"status": "ok", "role": role})
    except ValueError as e:
        return _roles_error(e)


@auth_bp.delete("/roles/<slug>")
@admin_required
def roles_delete(slug: str):
    try:
        roles_service.delete_role(slug)
        log_audit("delete_role", entity="app_roles", entity_id=slug)
        return jsonify({"status": "ok", "message": "Rol eliminado."})
    except ValueError as e:
        return _roles_error(e)


@auth_bp.get("/users")
@admin_required
def users_list():
    limit = min(int(request.args.get("limit", 100)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    data = user_store.list_users(limit=limit, offset=offset)
    assignable = roles_service.assignable_roles()
    return jsonify({"status": "ok", **data, "assignable_roles": assignable})


@auth_bp.patch("/users/<user_id>")
@admin_required
def users_patch(user_id: str):
    body = request.get_json(silent=True) or {}
    role = (body.get("role") or "").strip()
    if not role:
        return jsonify({"status": "error", "message": "Indique el rol."}), 400
    try:
        user = user_store.update_user_role(user_id, role)
        log_audit("update_user_role", entity="users", entity_id=user_id, details={"role": role})
        return jsonify({"status": "ok", "user": user})
    except ValueError as e:
        return _users_error(e)


def _roles_error(exc: ValueError):
    code = str(exc)
    messages = {
        "duplicate_slug": ("Ya existe un rol con ese identificador.", 409),
        "reserved_slug": ("Ese identificador está reservado.", 400),
        "not_found": ("Rol no encontrado.", 404),
        "system_role": ("No se puede eliminar un rol del sistema.", 409),
        "role_in_use": ("Hay usuarios con este rol.", 409),
        "pages_required": ("Seleccione al menos una página.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status


def _users_error(exc: ValueError):
    code = str(exc)
    messages = {
        "invalid_role": ("Rol no válido.", 400),
        "role_not_assignable": ("Este rol no se puede asignar.", 403),
        "not_found": ("Usuario no encontrado.", 404),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status


def _profile_error(exc: ValueError):
    code = str(exc)
    messages = {
        "not_found": ("Usuario no encontrado.", 404),
        "invalid_current_password": ("La contraseña actual no es correcta.", 401),
        "duplicate_email": ("Ya existe una cuenta con ese correo.", 409),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status


@auth_bp.post("/forgot-password")
def forgot_password():
    body = request.get_json(silent=True) or {}
    email = normalize_email(body.get("email", ""))
    if not email:
        return jsonify({"status": "error", "message": "Indica tu correo electrónico."}), 400
    from auth import password_reset

    password_reset.create_reset_token(email)
    return jsonify(
        {
            "status": "ok",
            "message": "Si el correo existe, recibirás un código en Notificaciones para restablecer tu contraseña.",
        }
    )


@auth_bp.post("/reset-password")
def reset_password_route():
    body = request.get_json(silent=True) or {}
    token = (body.get("token") or "").strip()
    new_password = body.get("new_password") or ""
    password_confirm = body.get("password_confirm", body.get("password2", ""))
    from auth import password_reset

    try:
        user = password_reset.reset_password(token, new_password, password_confirm)
    except ValueError as e:
        return _reset_error(e)
    return jsonify({"status": "ok", "message": "Contraseña restablecida. Ya puedes iniciar sesión.", "user": user})


@auth_bp.get("/notifications")
@login_required
def notifications_list():
    from shared.notifications import list_for_email

    email = session.get("email") or ""
    data = list_for_email(email, limit=min(int(request.args.get("limit", 50)), 200))
    return jsonify({"status": "ok", **data})


@auth_bp.patch("/notifications/<int:notification_id>/read")
@login_required
def notifications_read_one(notification_id: int):
    from shared.notifications import mark_read

    ok = mark_read(notification_id, session.get("email") or "")
    if not ok:
        return jsonify({"status": "error", "message": "Notificación no encontrada."}), 404
    return jsonify({"status": "ok"})


@auth_bp.post("/notifications/read-all")
@login_required
def notifications_read_all():
    from shared.notifications import mark_all_read

    n = mark_all_read(session.get("email") or "")
    return jsonify({"status": "ok", "marked": n})


def _reset_error(exc: ValueError):
    code = str(exc)
    messages = {
        "token_required": ("Indica el código de recuperación.", 400),
        "weak_password": ("La contraseña no cumple los requisitos.", 400),
        "password_mismatch": ("Las contraseñas no coinciden.", 400),
        "invalid_token": ("Código inválido o ya utilizado.", 400),
        "expired_token": ("El código expiró. Solicita uno nuevo.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status
