# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Blueprint, jsonify, request, session
from pathlib import Path
import uuid

from auth import roles_service, users as user_store
from auth.decorators import login_required, permission_required
from auth.validators import normalize_email, validate_login, validate_profile_update, validate_register
from shared.audit import log_audit
from shared.rate_limit import check_rate_limit, clear_attempts, consume_attempt, record_attempt
from shared.roles_registry import ADMIN_ROLE, DEFAULT_REGISTER_ROLE

auth_bp = Blueprint("auth", __name__)


def _client_key() -> str:
    return request.remote_addr or "unknown"


def _login_keys(email: str) -> tuple[str, str]:
    """Limita tanto ataques desde una IP como intentos dirigidos a una cuenta."""
    return _client_key(), normalize_email(email) or "unknown-account"


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
    rate_msg = check_rate_limit(
        "register", _client_key(), max_attempts=5, window_sec=900
    )
    if rate_msg:
        return jsonify({"status": "error", "message": rate_msg}), 429

    record_attempt("register", _client_key())

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
    data = request.get_json(silent=True) or {}
    raw = data.get("email") or data.get("username") or ""
    email = normalize_email(raw)
    password = data.get("password", "")
    ip_key, account_key = _login_keys(email)
    rate_msg = (
        consume_attempt("login_ip", ip_key, max_attempts=12, window_sec=900)
        or consume_attempt("login_account", account_key, max_attempts=8, window_sec=900)
    )
    if rate_msg:
        return jsonify({"status": "error", "message": rate_msg, "code": "rate_limited"}), 429

    errors = validate_login(email, password)
    if errors:
        return jsonify({"status": "error", "message": "Datos inválidos.", "errors": errors}), 400

    doc = user_store.find_by_email(email)
    if not doc or not user_store.verify_password(doc, password):
        return jsonify(
            {"status": "error", "message": "Correo o contraseña incorrectos."},
        ), 401

    clear_attempts("login_ip", ip_key)
    clear_attempts("login_account", account_key)
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


@auth_bp.get("/profile/suggestions")
@login_required
def profile_suggestions():
    doc = user_store.find_by_id(session["user_id"])
    if not doc:
        return jsonify({"status": "error", "message": "Usuario no encontrado."}), 404
    return jsonify({"status": "ok", "suggestions": user_store.profile_suggestions(doc)})


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
        phone=body.get("phone") or "",
        language=body.get("language") or "es",
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
            profile_data=body,
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
        {"status": "ok", "message": "Perfil actualizado.", "user": user, "access": _access_for_session()}
    )


@auth_bp.post("/profile/avatar")
@login_required
def profile_avatar():
    upload = request.files.get("avatar") or request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"status": "error", "message": "Selecciona una imagen."}), 400
    raw = upload.read()
    if not raw or len(raw) > 3 * 1024 * 1024:
        return jsonify({"status": "error", "message": "La imagen debe pesar menos de 3 MB."}), 400
    signatures = [(b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg")]
    suffix = next((ext for signature, ext in signatures if raw.startswith(signature)), None)
    if suffix is None and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        suffix = ".webp"
    if not suffix:
        return jsonify({"status": "error", "message": "Usa una imagen PNG, JPG o WebP."}), 400
    root = Path(__file__).resolve().parents[2]
    directory = root / "frontend" / "static" / "uploads" / "avatars"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{session['user_id']}_{uuid.uuid4().hex[:10]}{suffix}"
    (directory / filename).write_bytes(raw)
    avatar_url = f"/static/uploads/avatars/{filename}"
    try:
        user = user_store.update_avatar(session["user_id"], avatar_url)
    except ValueError:
        (directory / filename).unlink(missing_ok=True)
        return jsonify({"status": "error", "message": "Usuario no encontrado."}), 404
    return jsonify({"status": "ok", "avatar_url": avatar_url, "user": user})


@auth_bp.get("/roles")
@permission_required("users.manage")
def roles_list():
    return jsonify({"status": "ok", "roles": roles_service.list_roles()})


@auth_bp.post("/roles")
@permission_required("users.manage")
def roles_create():
    body = request.get_json(silent=True) or {}
    try:
        role = roles_service.create_role(body)
        log_audit("create_role", entity="app_roles", entity_id=role["slug"])
        return jsonify({"status": "ok", "role": role}), 201
    except ValueError as e:
        return _roles_error(e)


@auth_bp.put("/roles/<slug>")
@permission_required("users.manage")
def roles_update(slug: str):
    body = request.get_json(silent=True) or {}
    try:
        role = roles_service.update_role(slug, body)
        log_audit("update_role", entity="app_roles", entity_id=slug, details=body)
        return jsonify({"status": "ok", "role": role})
    except ValueError as e:
        return _roles_error(e)


@auth_bp.delete("/roles/<slug>")
@permission_required("users.manage")
def roles_delete(slug: str):
    try:
        result = roles_service.disable_role(slug)
        log_audit(
            "disable_role",
            entity="app_roles",
            entity_id=slug,
            details=result,
        )
        return jsonify(
            {
                "status": "ok",
                "message": (
                    f"Rol inhabilitado. {result['users_reassigned']} usuario(s) pasaron a "
                    f"{result['fallback_role']}."
                ),
                **result,
            }
        )
    except ValueError as e:
        return _roles_error(e)


@auth_bp.post("/roles/<slug>/inhabilitar")
@permission_required("users.manage")
def roles_disable(slug: str):
    try:
        result = roles_service.disable_role(slug)
        log_audit(
            "disable_role",
            entity="app_roles",
            entity_id=slug,
            details=result,
        )
        return jsonify(
            {
                "status": "ok",
                "message": (
                    f"Rol inhabilitado. {result['users_reassigned']} usuario(s) pasaron a "
                    f"{result['fallback_role']}."
                ),
                **result,
            }
        )
    except ValueError as e:
        return _roles_error(e)


@auth_bp.post("/roles/<slug>/habilitar")
@permission_required("users.manage")
def roles_enable(slug: str):
    try:
        result = roles_service.enable_role(slug)
        log_audit(
            "enable_role",
            entity="app_roles",
            entity_id=slug,
            details=result,
        )
        return jsonify(
            {
                "status": "ok",
                "message": (
                    "Rol habilitado. Vuelve a asignarlo a los usuarios que lo necesiten."
                ),
                **result,
            }
        )
    except ValueError as e:
        return _roles_error(e)


@auth_bp.get("/users")
@permission_required("users.manage")
def users_list():
    limit = min(int(request.args.get("limit", 100)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    q = (request.args.get("q") or request.args.get("search") or "").strip() or None
    data = user_store.list_users(limit=limit, offset=offset, q=q)
    assignable = roles_service.assignable_roles()
    return jsonify({"status": "ok", **data, "assignable_roles": assignable})


@auth_bp.patch("/users/<user_id>")
@permission_required("users.manage")
def users_patch(user_id: str):
    body = request.get_json(silent=True) or {}
    role = (body.get("role") or "").strip()
    if not role:
        return jsonify({"status": "error", "message": "Indique el rol."}), 400
    try:
        user = user_store.update_user_role(user_id, role, actor_id=session.get("user_id"))
        log_audit("update_user_role", entity="users", entity_id=user_id, details={"role": role})
        return jsonify({"status": "ok", "user": user})
    except ValueError as e:
        return _users_error(e)


@auth_bp.post("/users/<user_id>/inhabilitar")
@permission_required("users.manage")
def users_deactivate(user_id: str):
    try:
        user = user_store.deactivate_user(user_id, actor_id=session.get("user_id"))
        log_audit("deactivate_user", entity="users", entity_id=user_id, details={"email": user.get("email")})
        return jsonify(
            {
                "status": "ok",
                "message": f"Cuenta {user.get('email', '')} desactivada.",
                "user": user,
            }
        )
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
        "protected_role": ("Este rol no se puede editar ni inhabilitar.", 409),
        "already_inactive": ("Este rol ya está inhabilitado.", 409),
        "already_active": ("Este rol ya está activo.", 409),
        "role_inactive": ("Este rol está inhabilitado.", 409),
        "pages_required": ("Seleccione al menos una página.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status


def _users_error(exc: ValueError):
    code = str(exc)
    messages = {
        "invalid_role": ("Rol no válido.", 400),
        "role_not_assignable": ("Este rol no se puede asignar.", 403),
        "role_inactive": ("Este rol está inhabilitado.", 403),
        "not_found": ("Usuario no encontrado.", 404),
        "cannot_change_own_role": ("No puedes cambiar tu propio rol.", 409),
        "cannot_change_last_admin": ("Debe quedar al menos un administrador activo.", 409),
        "cannot_deactivate_self": ("No puedes desactivar tu propia cuenta.", 409),
        "last_admin": ("No puedes desactivar al último administrador.", 409),
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


@auth_bp.get("/notifications/pulse")
@login_required
def notifications_pulse():
    from shared.notifications import pulse_for_email

    email = session.get("email") or ""
    after = int(request.args.get("after", 0) or 0)
    data = pulse_for_email(email, after_id=after)
    return jsonify({"status": "ok", **data})


@auth_bp.get("/notifications")
@login_required
def notifications_list():
    from shared.notifications import list_for_email

    email = session.get("email") or ""
    data = list_for_email(
        email, limit=min(int(request.args.get("limit", 50)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
        unread_only=request.args.get("unread", "").lower() in ("1", "true", "yes"),
        category=(request.args.get("category") or "").strip() or None,
        q=(request.args.get("q") or "").strip() or None,
    )
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


@auth_bp.post("/notifications/read-category")
@login_required
def notifications_read_category():
    from shared.notifications import mark_category_read

    body = request.get_json(silent=True) or {}
    try:
        n = mark_category_read(session.get("email") or "", body.get("category") or "")
        return jsonify({"status": "ok", "marked": n})
    except ValueError:
        return jsonify({"status": "error", "message": "Indica una categoría.", "code": "category_required"}), 400
