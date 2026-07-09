"""Rutas Flask — paquete Q4 Datos."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth.decorators import admin_required, login_required
from paquetes.datos import services

datos_bp = Blueprint("datos", __name__, url_prefix="/api")


@datos_bp.get("/master/tables")
def master_tables():
    return jsonify({"status": "ok", "tables": services.list_tables()})


@datos_bp.get("/master/<name>")
def master_list(name: str):
    try:
        data = services.list_rows(
            name,
            limit=min(int(request.args.get("limit", 50)), 200),
            offset=max(int(request.args.get("offset", 0)), 0),
            search=(request.args.get("search") or request.args.get("q") or "").strip() or None,
        )
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        code = str(e)
        if code == "unknown_table":
            return jsonify({"status": "error", "message": "Tabla maestra no encontrada."}), 404
        raise


@datos_bp.get("/master/<name>/<row_id>")
def master_get(name: str, row_id: str):
    try:
        row = services.get_row(name, row_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Tabla maestra no encontrada."}), 404
    if not row:
        return jsonify({"status": "error", "message": "Registro no encontrado."}), 404
    return jsonify({"status": "ok", "row": row})


@datos_bp.post("/master/<name>")
@admin_required
def master_create(name: str):
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_row(name, body)
        return jsonify({"status": "ok", "row": row}), 201
    except ValueError as e:
        return _master_error(e)


@datos_bp.put("/master/<name>/<row_id>")
@admin_required
def master_update(name: str, row_id: str):
    body = request.get_json(silent=True) or {}
    try:
        row = services.update_row(name, row_id, body)
        return jsonify({"status": "ok", "row": row})
    except ValueError as e:
        return _master_error(e)


@datos_bp.delete("/master/<name>/<row_id>")
@admin_required
def master_delete(name: str, row_id: str):
    try:
        services.delete_row(name, row_id)
        return jsonify({"status": "ok", "message": "Registro eliminado."})
    except ValueError as e:
        return _master_error(e)


@datos_bp.post("/master/dim_producto/<int:product_id>/image")
@admin_required
def product_image(product_id: int):
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Archivo requerido (campo file)."}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"status": "error", "message": "Nombre de archivo vacío."}), 400
    try:
        url = services.save_product_image(product_id, f.filename, f.read())
        return jsonify({"status": "ok", "image_url": url})
    except ValueError as e:
        return _master_error(e)


@datos_bp.post("/build_model")
@admin_required
def build_model():
    try:
        stats = services.run_build_model()
        return jsonify({"status": "ok", "message": "Modelo reconstruido.", **stats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@datos_bp.post("/load_dataset")
@admin_required
def load_dataset():
    body = request.get_json(silent=True) or {}
    try:
        result = services.run_load_dataset(body.get("csv_path"))
        return jsonify({"status": "ok", **result})
    except ValueError as e:
        if str(e) == "csv_not_found":
            return jsonify({"status": "error", "message": "Archivo CSV no encontrado."}), 404
        raise
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@datos_bp.get("/elt_status")
def elt_status():
    return jsonify({"status": "ok", **services.get_elt_status()})


@datos_bp.get("/audit_log")
@login_required
def audit_log():
    data = services.list_audit_log(
        limit=min(int(request.args.get("limit", 50)), 200),
        offset=max(int(request.args.get("offset", 0)), 0),
    )
    return jsonify({"status": "ok", **data})


@datos_bp.get("/schema")
def schema_summary():
    return jsonify({"status": "ok", "tables": services.list_tables()})


def _master_error(exc: ValueError):
    code = str(exc)
    messages = {
        "unknown_table": ("Tabla maestra no encontrada.", 404),
        "read_only": ("Esta tabla es solo lectura.", 403),
        "not_found": ("Registro no encontrado.", 404),
        "duplicate_pk": ("Ya existe un registro con ese identificador.", 409),
        "has_children": ("No se puede eliminar: hay registros relacionados.", 409),
        "invalid_image_type": ("Formato no permitido. Use JPG, PNG o WEBP.", 400),
        "image_too_large": ("Imagen demasiado grande.", 400),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status
