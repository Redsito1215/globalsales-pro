# -*- coding: utf-8 -*-
"""Validación de entrada — seguridad y adecuación funcional (ISO/IEC 25010)."""
from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_NAME_RE = re.compile(r"^[\w\sáéíóúÁÉÍÓÚñÑüÜ.'\-]{2,100}$", re.UNICODE)


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def validate_register(email: str, password: str, password_confirm: str, name: str) -> dict[str, str]:
    errors: dict[str, str] = {}
    email = normalize_email(email)
    name = (name or "").strip()
    password = password or ""
    password_confirm = password_confirm or ""

    if not email:
        errors["email"] = "El correo electrónico es obligatorio."
    elif len(email) > 254 or not _EMAIL_RE.match(email):
        errors["email"] = "Ingresa un correo electrónico válido."

    if not name:
        errors["name"] = "El nombre es obligatorio."
    elif not _NAME_RE.match(name):
        errors["name"] = "El nombre debe tener entre 2 y 100 caracteres (solo letras y espacios)."

    if not password:
        errors["password"] = "La contraseña es obligatoria."
    elif len(password) < 8:
        errors["password"] = "La contraseña debe tener al menos 8 caracteres."
    elif len(password) > 128:
        errors["password"] = "La contraseña no puede superar 128 caracteres."
    elif not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors["password"] = "La contraseña debe incluir al menos una letra y un número."

    if password != password_confirm:
        errors["password_confirm"] = "Las contraseñas no coinciden."

    return errors


def validate_login(email: str, password: str) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not normalize_email(email):
        errors["email"] = "El correo electrónico es obligatorio."
    if not password:
        errors["password"] = "La contraseña es obligatoria."
    return errors
