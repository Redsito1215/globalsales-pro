#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crea usuarios demo por rol (idempotente). Uso: python scripts/seed_demo.py"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from auth import roles_service, users as user_store  # noqa: E402

DEMO_USERS = [
    ("admin@globtrade.demo", "Administrador", "administrador"),
    ("vendedor@globtrade.demo", "Vendedor", "vendedor"),
    ("analista@globtrade.demo", "Analista", "analista"),
    ("cliente@globtrade.demo", "Cliente", "cliente"),
]
DEFAULT_PASSWORD = "Demo1234!"


def ensure_demo_roles_ready() -> list[str]:
    """Reactiva roles de sistema demo que hayan quedado inhabilitados."""
    from shared.roles_registry import ADMIN_ROLE, DEFAULT_ROLES

    fixed = []
    col = roles_service._col()
    for role in DEFAULT_ROLES:
        slug = role["slug"]
        if slug == ADMIN_ROLE:
            continue
        doc = col.find_one({"slug": slug}, {"active": 1})
        if doc and doc.get("active") is False:
            roles_service.enable_role(slug)
            fixed.append(slug)
    return fixed


def seed_users(password: str, force: bool) -> list[str]:
    roles_service.ensure_roles_seed()
    ensure_demo_roles_ready()
    created = []
    for email, name, role in DEMO_USERS:
        existing = user_store.find_by_email(email)
        if existing and not force:
            if (
                existing.get("role") != role
                or existing.get("active") is False
                or existing.get("name") != name
            ):
                user_store._col().update_one(
                    {"email": email},
                    {"$set": {"role": role, "active": True, "name": name}},
                )
                print(f"  ~ {email} ({role}) — cuenta sincronizada")
            else:
                print(f"  · {email} ({role}) — ya existe, omitido")
            continue
        if existing and force:
            from auth import users as us

            us._col().delete_one({"email": email})
        user_store.create_user(email=email, password=password, name=name, role=role)
        created.append(email)
        print(f"  + {email} ({role})")
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Usuarios demo GLOBTRADE por rol")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Contraseña para todas las cuentas demo")
    parser.add_argument("--force", action="store_true", help="Recrear cuentas demo si ya existen")
    args = parser.parse_args()

    print("GLOBTRADE — seed demo")
    print(f"Contraseña: {args.password}")
    try:
        created = seed_users(args.password, args.force)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if created:
        print(f"\nListo: {len(created)} cuenta(s) creada(s).")
    else:
        print("\nNada nuevo (usa --force para recrear).")
    print("\nInicia sesión con cualquier correo @globtrade.demo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
