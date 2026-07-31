"""Roles configurables — persistencia y consultas."""
from __future__ import annotations

import re
from typing import Any

from shared.mongo import get_db
from shared.roles_registry import (
    DEFAULT_ROLES,
    PAGE_CATALOG,
    PERMISSION_CATALOG,
    PUBLIC_PAGES,
)

COLLECTION = "app_roles"


def _col():
    return get_db()[COLLECTION]


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "rol"


def ensure_roles_seed() -> None:
    col = _col()
    for role in DEFAULT_ROLES:
        col.update_one({"slug": role["slug"]}, {"$setOnInsert": dict(role)}, upsert=True)
    # Actualizar administrador con todas las páginas/permisos si faltan nuevas
    all_pages = list(PAGE_CATALOG.keys())
    all_perms = list(PERMISSION_CATALOG.keys())
    col.update_one(
        {"slug": "administrador"},
        {"$set": {"pages": all_pages, "permissions": all_perms}},
    )
    col.update_one(
        {"slug": "cliente"},
        {
            "$set": {
                "pages": ["tienda", "company", "mis-pedidos", "soporte", "notificaciones"],
                "permissions": ["shop.view", "shop.checkout"],
            }
        },
    )
    col.update_one(
        {"slug": "vendedor"},
        {
            "$setOnInsert": {
                "slug": "vendedor",
                "label": "Vendedor comercial",
                "system": True,
                "assignable": True,
            },
            "$set": {
                "pages": [
                    "tienda",
                    "company",
                    "ventas",
                    "compras",
                    "reportes",
                    "reportes-compuestos",
                    "orders",
                    "decisiones",
                    "mis-pedidos",
                    "soporte",
                    "notificaciones",
                ],
                "permissions": [
                    "shop.view",
                    "shop.checkout",
                    "ventas.manage",
                    "compras.manage",
                    "reportes.view",
                    "orders.read",
                    "soporte.inbox",
                    "decisiones.view",
                ],
            },
        },
        upsert=True,
    )
    col.update_one(
        {"slug": "analista"},
        {
            "$set": {
                "pages": [
                    "dashboard",
                    "catalogo",
                    "company",
                    "trends",
                    "regions",
                    "products",
                    "export",
                    "decisiones",
                    "reportes-compuestos",
                    "tienda",
                    "orders",
                    "ventas",
                    "reportes",
                    "soporte",
                    "notificaciones",
                ],
                "permissions": [
                    "shop.view",
                    "orders.read",
                    "analysis.export",
                    "decisiones.view",
                    "reportes.view",
                ],
            }
        },
    )


def list_roles() -> list[dict[str, Any]]:
    ensure_roles_seed()
    rows = list(_col().find({}, {"_id": 0}).sort("slug", 1))
    return rows


def get_role(slug: str) -> dict[str, Any] | None:
    ensure_roles_seed()
    return _col().find_one({"slug": slug}, {"_id": 0})


def role_exists(slug: str) -> bool:
    return _col().count_documents({"slug": slug}) > 0


def pages_for_role(slug: str | None) -> list[str]:
    if not slug:
        return list(PUBLIC_PAGES)
    role = get_role(slug)
    if not role:
        return list(PUBLIC_PAGES)
    pages = role.get("pages") or []
    return pages if pages else list(PUBLIC_PAGES)


def permissions_for_role(slug: str | None) -> list[str]:
    if not slug:
        return []
    role = get_role(slug)
    if not role:
        return []
    return list(role.get("permissions") or [])


def has_permission(slug: str | None, permission: str) -> bool:
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
    out = [p for p in pages if p in valid]
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
    existing = get_role(slug)
    if not existing:
        raise ValueError("not_found")
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


def delete_role(slug: str) -> None:
    existing = get_role(slug)
    if not existing:
        raise ValueError("not_found")
    if existing.get("system"):
        raise ValueError("system_role")
    db = get_db()
    if db["users"].count_documents({"role": slug, "active": True}):
        raise ValueError("role_in_use")
    _col().delete_one({"slug": slug})


def assignable_roles() -> list[dict[str, Any]]:
    ensure_roles_seed()
    return list(_col().find({"assignable": True}, {"_id": 0, "slug": 1, "label": 1}).sort("label", 1))
