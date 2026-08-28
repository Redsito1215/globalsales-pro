"""Roles configurables — persistencia y consultas."""
from __future__ import annotations

import re
from typing import Any

from shared.mongo import get_collection, get_ops_db
from shared.roles_registry import (
    ADMIN_ROLE,
    DEFAULT_REGISTER_ROLE,
    DEFAULT_ROLES,
    PAGE_CATALOG,
    PERMISSION_CATALOG,
    PUBLIC_PAGES,
)

COLLECTION = "app_roles"


def _col():
    return get_collection(COLLECTION)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "rol"


def ensure_roles_seed() -> None:
    """Siembra roles por defecto sin pisar páginas/permisos ya personalizados."""
    col = _col()
    for row in col.find({"pages": "datos"}, {"_id": 1, "pages": 1}):
        pages = [_normalize_page_id(p) for p in (row.get("pages") or [])]
        deduped: list[str] = []
        for p in pages:
            if p in PAGE_CATALOG and p not in deduped:
                deduped.append(p)
        col.update_one({"_id": row["_id"]}, {"$set": {"pages": deduped}})
    for role in DEFAULT_ROLES:
        slug = role["slug"]
        existing = col.find_one({"slug": slug}, {"active": 1})
        patch: dict[str, Any] = {
            "label": role["label"],
            "system": bool(role.get("system")),
        }
        if not existing or existing.get("active") is not False:
            patch["assignable"] = bool(role.get("assignable", True))
        col.update_one(
            {"slug": slug},
            {
                "$setOnInsert": {
                    "slug": slug,
                    "pages": list(role.get("pages") or []),
                    "permissions": list(role.get("permissions") or []),
                    "active": True,
                },
                "$set": patch,
            },
            upsert=True,
        )
    col.update_one(
        {"slug": ADMIN_ROLE},
        {"$addToSet": {"permissions": {"$each": list(PERMISSION_CATALOG.keys())}}},
    )
    # Nueva consola táctica: disponible para los dos roles internos estándar.
    for slug in ("vendedor", "analista"):
        col.update_one(
            {"slug": slug, "active": {"$ne": False}},
            {"$addToSet": {"pages": "profesional"}},
        )


def list_roles() -> list[dict[str, Any]]:
    ensure_roles_seed()
    rows = list(_col().find({}, {"_id": 0}).sort("slug", 1))
    for row in rows:
        if row.get("active") is not False:
            row["active"] = True
    return rows


def _role_is_active(role: dict[str, Any] | None) -> bool:
    if not role:
        return False
    return role.get("active") is not False


def get_role(slug: str) -> dict[str, Any] | None:
    ensure_roles_seed()
    row = _col().find_one({"slug": slug}, {"_id": 0})
    if row and row.get("active") is not False:
        row["active"] = True
    return row


def role_exists(slug: str) -> bool:
    return _col().count_documents({"slug": slug}) > 0


def _normalize_page_id(page_id: str) -> str:
    return "gestion" if page_id == "datos" else page_id


def pages_for_role(slug: str | None) -> list[str]:
    if not slug:
        return list(PUBLIC_PAGES)
    if slug == ADMIN_ROLE:
        return list(PAGE_CATALOG.keys())
    role = get_role(slug)
    if not role or not _role_is_active(role):
        return list(PUBLIC_PAGES)
    pages = [_normalize_page_id(p) for p in (role.get("pages") or [])]
    pages = [p for p in pages if p in PAGE_CATALOG]
    return pages if pages else list(PUBLIC_PAGES)


def permissions_for_role(slug: str | None) -> list[str]:
    if not slug:
        return []
    if slug == ADMIN_ROLE:
        return list(PERMISSION_CATALOG.keys())
    role = get_role(slug)
    if not role or not _role_is_active(role):
        return []
    return list(role.get("permissions") or [])


def has_permission(slug: str | None, permission: str) -> bool:
    if slug == ADMIN_ROLE:
        return True
    perms = permissions_for_role(slug)
    return "*" in perms or permission in perms


def access_payload(role_slug: str | None) -> dict[str, Any]:
    pages = pages_for_role(role_slug)
    perms = permissions_for_role(role_slug)
    return {
        "pages": pages,
        "permissions": perms,
        "page_catalog": PAGE_CATALOG,
        "permission_catalog": PERMISSION_CATALOG,
        "sections": {k: v for k, v in PAGE_CATALOG.items()},
    }


def _validate_pages(pages: list[str]) -> list[str]:
    valid = set(PAGE_CATALOG.keys())
    out: list[str] = []
    for p in pages:
        p = _normalize_page_id(p)
        if p in valid and p not in out:
            out.append(p)
    if not out:
        raise ValueError("pages_required")
    return out


def _validate_permissions(permissions: list[str]) -> list[str]:
    valid = set(PERMISSION_CATALOG.keys())
    return [p for p in permissions if p in valid]


def create_role(data: dict[str, Any]) -> dict[str, Any]:
    slug = _slugify(data.get("slug") or data.get("label") or "")
    if role_exists(slug):
        raise ValueError("duplicate_slug")
    if slug in {"administrador", "cliente", "analista"}:
        raise ValueError("reserved_slug")
    doc = {
        "slug": slug,
        "label": (data.get("label") or slug).strip(),
        "system": False,
        "assignable": bool(data.get("assignable", True)),
        "pages": _validate_pages(list(data.get("pages") or ["tienda"])),
        "permissions": _validate_permissions(list(data.get("permissions") or [])),
    }
    _col().insert_one(doc)
    return dict(doc)


def update_role(slug: str, data: dict[str, Any]) -> dict[str, Any]:
    if slug == ADMIN_ROLE:
        raise ValueError("protected_role")
    existing = get_role(slug)
    if not existing:
        raise ValueError("not_found")
    if not _role_is_active(existing):
        raise ValueError("role_inactive")
    patch: dict[str, Any] = {}
    if "label" in data and data["label"]:
        patch["label"] = str(data["label"]).strip()
    if "assignable" in data:
        patch["assignable"] = bool(data["assignable"])
    if "pages" in data:
        patch["pages"] = _validate_pages(list(data["pages"]))
    if "permissions" in data:
        patch["permissions"] = _validate_permissions(list(data["permissions"]))
    if patch:
        _col().update_one({"slug": slug}, {"$set": patch})
    return get_role(slug) or {}


def disable_role(slug: str) -> dict[str, Any]:
    """Inhabilita un rol y reasigna sus usuarios al rol cliente (usuario normal)."""
    existing = get_role(slug)
    if not existing:
        raise ValueError("not_found")
    if slug in {ADMIN_ROLE, DEFAULT_REGISTER_ROLE}:
        raise ValueError("protected_role")
    if not _role_is_active(existing):
        raise ValueError("already_inactive")
    db = get_ops_db()
    moved = db["users"].count_documents({"role": slug, "active": True})
    db["users"].update_many(
        {"role": slug, "active": True},
        {"$set": {"role": DEFAULT_REGISTER_ROLE}},
    )
    _col().update_one({"slug": slug}, {"$set": {"active": False, "assignable": False}})
    return {"slug": slug, "users_reassigned": moved, "fallback_role": DEFAULT_REGISTER_ROLE}


def _default_assignable(slug: str) -> bool:
    for role in DEFAULT_ROLES:
        if role["slug"] == slug:
            return bool(role.get("assignable", True))
    return True


def enable_role(slug: str) -> dict[str, Any]:
    """Reactiva un rol inhabilitado (no reasigna usuarios automáticamente)."""
    existing = get_role(slug)
    if not existing:
        raise ValueError("not_found")
    if slug == ADMIN_ROLE:
        raise ValueError("protected_role")
    if _role_is_active(existing):
        raise ValueError("already_active")
    assignable = _default_assignable(slug)
    _col().update_one({"slug": slug}, {"$set": {"active": True, "assignable": assignable}})
    return {"slug": slug, "assignable": assignable}


def delete_role(slug: str) -> None:
    """Compatibilidad: inhabilitar en lugar de borrar."""
    disable_role(slug)


def assignable_roles() -> list[dict[str, Any]]:
    ensure_roles_seed()
    return list(
        _col()
        .find(
            {
                "assignable": True,
                "active": {"$ne": False},
                "slug": {"$ne": ADMIN_ROLE},
            },
            {"_id": 0, "slug": 1, "label": 1},
        )
        .sort("label", 1)
    )
