# -*- coding: utf-8 -*-
"""Perfil comercial de la empresa (facturas, documentos)."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from config.settings import settings
from shared.mongo import get_ops_db

DOC_ID = "company_profile"
ALLOWED_LOGO_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

DEFAULT_COMPANY_PROFILE: dict[str, Any] = {
    "name": "GLOBTRADE",
    "legal_name": "GLOBTRADE S.A.",
    "tagline": "Distribución comercial internacional",
    "logo_url": "/static/img/globtrade-logo.png",
    "address": "",
    "city": "",
    "country": "",
    "email": "contacto@globtrade.com",
    "phone": "",
    "tax_id": "",
    "website": "www.globtrade.com",
    "invoice_footer": "Documento comercial GLOBTRADE (demo académica). No es factura fiscal.",
    "invoice_signer": "Equipo Comercial GLOBTRADE",
}


def _public_fields() -> tuple[str, ...]:
    return tuple(DEFAULT_COMPANY_PROFILE.keys())


def _normalize(payload: dict[str, Any] | None) -> dict[str, Any]:
    src = payload or {}
    out = dict(DEFAULT_COMPANY_PROFILE)
    for key in _public_fields():
        if key in src and src[key] is not None:
            out[key] = str(src[key]).strip()
    if not out["name"]:
        out["name"] = DEFAULT_COMPANY_PROFILE["name"]
    if not out["legal_name"]:
        out["legal_name"] = DEFAULT_COMPANY_PROFILE["legal_name"]
    return out


def get_company_profile(*, create: bool = True) -> dict[str, Any]:
    db = get_ops_db()
    doc = db["app_meta"].find_one({"_id": DOC_ID})
    if not doc:
        profile = dict(DEFAULT_COMPANY_PROFILE)
        if create:
            db["app_meta"].update_one({"_id": DOC_ID}, {"$set": profile}, upsert=True)
        return profile
    merged = _normalize(doc)
    return merged


def update_company_profile(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_company_profile(create=True)
    data = dict(current)
    editable = set(_public_fields()) - {"logo_url"}
    for key in editable:
        if key in payload:
            data[key] = str(payload.get(key) or "").strip()
    data = _normalize(data)
    get_ops_db()["app_meta"].update_one({"_id": DOC_ID}, {"$set": data}, upsert=True)
    return data


def static_path_from_url(url: str | None) -> Path | None:
    if not url:
        return None
    raw = str(url).strip()
    if raw.startswith("/static/"):
        return settings.static_dir / raw[len("/static/") :]
    if raw.startswith("static/"):
        return settings.static_dir / raw[7:]
    return None


def save_company_logo(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_LOGO_EXT:
        raise ValueError("invalid_image_type")
    max_bytes = settings.max_product_image_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValueError("image_too_large")
    dest_dir = settings.company_uploads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"logo_{uuid.uuid4().hex[:10]}{ext}"
    path = dest_dir / safe_name
    path.write_bytes(raw)
    url = f"/static/uploads/company/{safe_name}"
    profile = get_company_profile(create=True)
    profile["logo_url"] = url
    get_ops_db()["app_meta"].update_one({"_id": DOC_ID}, {"$set": profile}, upsert=True)
    return url
