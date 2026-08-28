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
    "name": "Altavia Trade",
    "legal_name": "Altavia Trade",
    "tagline": "Distribución comercial internacional",
    "logo_url": "/static/img/altavia-trade-logo.png",
    "storefront_hero_image_url": "/static/img/products/88.jpg",
    "storefront_hero_kicker": "Comercio mayorista B2B",
    "storefront_hero_title": "Abastece tu negocio con catálogo global",
    "storefront_hero_lead": "Pedidos consolidados, envío coordinado y seguimiento en Mis pedidos — todo desde un solo lugar.",
    "storefront_hero_cta": "Ver catálogo",
    "storefront_heroes": [],
    "address": "",
    "city": "",
    "country": "",
    "email": "contacto@altaviatrade.com",
    "phone": "",
    "tax_id": "",
    "website": "www.altaviatrade.com",
    "invoice_footer": "Factura comercial Altavia Trade. Conserve este documento.",
    "invoice_signer": "Equipo Comercial Altavia Trade",
    "tax_rate": "15",
}


def _public_fields() -> tuple[str, ...]:
    return tuple(DEFAULT_COMPANY_PROFILE.keys())


def _normalize(payload: dict[str, Any] | None) -> dict[str, Any]:
    src = payload or {}
    out = dict(DEFAULT_COMPANY_PROFILE)
    for key in _public_fields():
        if key in src and src[key] is not None:
            if key == "storefront_heroes":
                heroes = src[key] if isinstance(src[key], list) else []
                out[key] = [
                    {
                        "image_url": str(x.get("image_url") or "").strip(),
                        "kicker": str(x.get("kicker") or "").strip(),
                        "title": str(x.get("title") or "").strip(),
                        "lead": str(x.get("lead") or "").strip(),
                        "cta": str(x.get("cta") or "").strip(),
                    }
                    for x in heroes if isinstance(x, dict) and any(str(x.get(k) or "").strip() for k in ("image_url", "kicker", "title", "lead", "cta"))
                ][:8]
            else:
                out[key] = str(src[key]).strip()
    legacy_defaults = {
        "name": {"GLOBTRADE", "GLOBTRADE S.A."},
        "legal_name": {"GLOBTRADE", "GLOBTRADE S.A."},
        "logo_url": {"/static/img/globtrade-logo.png"},
        "email": {"contacto@globtrade.com"},
        "website": {"www.globtrade.com"},
        "invoice_footer": {"Factura comercial GLOBTRADE. Conserve este documento."},
        "invoice_signer": {"Equipo Comercial GLOBTRADE"},
    }
    for key, old_values in legacy_defaults.items():
        if out.get(key) in old_values:
            out[key] = DEFAULT_COMPANY_PROFILE[key]
    if not out["name"]:
        out["name"] = DEFAULT_COMPANY_PROFILE["name"]
    if not out["legal_name"]:
        out["legal_name"] = DEFAULT_COMPANY_PROFILE["legal_name"]
    footer = str(out.get("invoice_footer") or "")
    fl = footer.lower()
    if (
        "demo" in fl
        or "académ" in fl
        or "academica" in fl
        or "no es factura fiscal" in fl
    ):
        out["invoice_footer"] = DEFAULT_COMPANY_PROFILE["invoice_footer"]
    rate_raw = str(out.get("tax_rate") or DEFAULT_COMPANY_PROFILE["tax_rate"]).strip().replace(",", ".")
    try:
        rate = float(rate_raw)
    except ValueError:
        rate = 15.0
    out["tax_rate"] = str(int(rate) if rate == int(rate) else rate)
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
    editable = set(_public_fields()) - {"logo_url", "storefront_hero_image_url"}
    for key in editable:
        if key in payload:
            data[key] = payload.get(key) if key == "storefront_heroes" else str(payload.get(key) or "").strip()
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


def get_storefront_hero() -> dict[str, Any]:
    profile = get_company_profile(create=True)
    primary = {
        "image_url": profile.get("storefront_hero_image_url") or DEFAULT_COMPANY_PROFILE["storefront_hero_image_url"],
        "kicker": profile.get("storefront_hero_kicker") or DEFAULT_COMPANY_PROFILE["storefront_hero_kicker"],
        "title": profile.get("storefront_hero_title") or DEFAULT_COMPANY_PROFILE["storefront_hero_title"],
        "lead": profile.get("storefront_hero_lead") or DEFAULT_COMPANY_PROFILE["storefront_hero_lead"],
        "cta": profile.get("storefront_hero_cta") or DEFAULT_COMPANY_PROFILE["storefront_hero_cta"],
    }
    configured = profile.get("storefront_heroes") if isinstance(profile.get("storefront_heroes"), list) else []
    heroes = [primary] + [x for x in configured if isinstance(x, dict) and any(str(v or "").strip() for v in x.values())]
    return {**primary, "heroes": heroes[:8]}


def save_storefront_hero_image(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_LOGO_EXT:
        raise ValueError("invalid_image_type")
    max_bytes = settings.max_product_image_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValueError("image_too_large")
    dest_dir = settings.company_uploads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"storefront_hero_{uuid.uuid4().hex[:10]}{ext}"
    path = dest_dir / safe_name
    path.write_bytes(raw)
    url = f"/static/uploads/company/{safe_name}"
    profile = get_company_profile(create=True)
    profile["storefront_hero_image_url"] = url
    get_ops_db()["app_meta"].update_one({"_id": DOC_ID}, {"$set": profile}, upsert=True)
    return url


def save_storefront_slide_image(filename: str, raw: bytes) -> str:
    """Guarda una imagen para una diapositiva adicional sin alterar el banner principal."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_LOGO_EXT:
        raise ValueError("invalid_image_type")
    max_bytes = settings.max_product_image_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise ValueError("image_too_large")
    dest_dir = settings.company_uploads_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"storefront_slide_{uuid.uuid4().hex[:10]}{ext}"
    (dest_dir / safe_name).write_bytes(raw)
    return f"/static/uploads/company/{safe_name}"
