"""Rutas — perfil comercial de la empresa."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import login_required, permission_required
from shared.audit import log_audit
from shared.company_profile import (
    get_company_profile,
    get_storefront_hero,
    save_company_logo,
    save_storefront_hero_image,
    save_storefront_slide_image,
    update_company_profile,
)

empresa_bp = Blueprint("empresa", __name__, url_prefix="/api/empresa")


@empresa_bp.get("/storefront-hero")
def storefront_hero_get():
    profile = get_company_profile()
    public = {key: profile.get(key) for key in ("name", "legal_name", "tagline", "logo_url", "website", "email", "phone")}
    return jsonify({"status": "ok", "hero": get_storefront_hero(), "company": public})


@empresa_bp.get("/perfil")
@login_required
def perfil_get():
    return jsonify({"status": "ok", "profile": get_company_profile()})


@empresa_bp.put("/perfil")
@login_required
@permission_required("company.manage")
def perfil_put():
    body = request.get_json(silent=True) or {}
    try:
        profile = update_company_profile(body)
        log_audit("company_profile_update", entity="company_profile", details={"name": profile.get("name")})
        return jsonify({"status": "ok", "profile": profile})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@empresa_bp.post("/perfil/logo")
@login_required
@permission_required("company.manage")
def perfil_logo():
    f = request.files.get("file") or request.files.get("logo")
    if not f or not f.filename:
        return jsonify({"status": "error", "message": "Archivo de imagen requerido."}), 400
    try:
        url = save_company_logo(f.filename, f.read())
        profile = get_company_profile()
        log_audit("company_logo_upload", entity="company_profile", details={"logo_url": url})
        return jsonify({"status": "ok", "logo_url": url, "profile": profile})
    except ValueError as e:
        code = str(e)
        msg = {
            "invalid_image_type": "Formato no válido. Usa PNG, JPG o WebP.",
            "image_too_large": "La imagen supera el tamaño máximo permitido.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@empresa_bp.post("/perfil/storefront-hero")
@login_required
@permission_required("company.manage")
def perfil_storefront_hero():
    f = request.files.get("file") or request.files.get("image")
    if not f or not f.filename:
        return jsonify({"status": "error", "message": "Archivo de imagen requerido."}), 400
    try:
        url = save_storefront_hero_image(f.filename, f.read())
        profile = get_company_profile()
        log_audit("storefront_hero_upload", entity="company_profile", details={"image_url": url})
        return jsonify({"status": "ok", "image_url": url, "hero": get_storefront_hero(), "profile": profile})
    except ValueError as e:
        code = str(e)
        msg = {
            "invalid_image_type": "Formato no válido. Usa PNG, JPG o WebP.",
            "image_too_large": "La imagen supera el tamaño máximo permitido.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400


@empresa_bp.post("/perfil/storefront-slide")
@login_required
@permission_required("company.manage")
def perfil_storefront_slide():
    f = request.files.get("file") or request.files.get("image")
    if not f or not f.filename:
        return jsonify({"status": "error", "message": "Archivo de imagen requerido."}), 400
    try:
        url = save_storefront_slide_image(f.filename, f.read())
        log_audit("storefront_slide_upload", entity="company_profile", details={"image_url": url})
        return jsonify({"status": "ok", "image_url": url})
    except ValueError as e:
        code = str(e)
        msg = {
            "invalid_image_type": "Formato no válido. Usa PNG, JPG o WebP.",
            "image_too_large": "La imagen supera el tamaño máximo permitido.",
        }.get(code, code)
        return jsonify({"status": "error", "message": msg, "code": code}), 400
