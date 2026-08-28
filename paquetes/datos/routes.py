"""Rutas Flask — paquete Q4 Datos."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, jsonify, request

from auth.decorators import login_required, permission_required
from paquetes.datos import services
from shared.audit import log_audit
from paquetes.reportes.pdf_export import generate_report_pdf

datos_bp = Blueprint("datos", __name__, url_prefix="/api")


@datos_bp.get("/master/tables")
def master_tables():
    return jsonify({"status": "ok", "tables": services.list_editable_masters()})


@datos_bp.get("/master/<name>")
def master_list(name: str):
    try:
        active_arg = (request.args.get("active") or "").strip().lower()
        active = True if active_arg == "true" else False if active_arg == "false" else None
        category_raw = (request.args.get("category_id") or "").strip()
        vendor_raw = (request.args.get("vendor_id") or "").strip()
        if category_raw and not category_raw.isdigit():
            raise ValueError("invalid_filters")
        if vendor_raw and not vendor_raw.isdigit():
            raise ValueError("invalid_filters")
        data = services.list_rows(
            name,
            limit=min(int(request.args.get("limit", 50)), 200),
            offset=max(int(request.args.get("offset", 0)), 0),
            search=(request.args.get("search") or request.args.get("q") or "").strip() or None,
            active=active,
            category_id=int(category_raw) if category_raw else None,
            vendor_id=int(vendor_raw) if vendor_raw else None,
        )
        return jsonify({"status": "ok", **data})
    except ValueError as e:
        code = str(e)
        if code == "unknown_table":
            return jsonify({"status": "error", "message": "Tabla maestra no encontrada."}), 404
        if code == "invalid_filters":
            return jsonify({"status": "error", "message": "Los filtros de categoría o proveedor no son válidos."}), 400
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
@login_required
@permission_required("masters.write")
def master_create(name: str):
    body = request.get_json(silent=True) or {}
    try:
        row = services.create_row(name, body)
        return jsonify({"status": "ok", "row": row}), 201
    except ValueError as e:
        return _master_error(e)


@datos_bp.put("/master/<name>/<row_id>")
@login_required
@permission_required("masters.write")
def master_update(name: str, row_id: str):
    body = request.get_json(silent=True) or {}
    try:
        row = services.update_row(name, row_id, body)
        return jsonify({"status": "ok", "row": row})
    except ValueError as e:
        return _master_error(e)


@datos_bp.delete("/master/<name>/<row_id>")
@login_required
@permission_required("masters.write")
def master_delete(name: str, row_id: str):
    try:
        services.delete_row(name, row_id)
        return jsonify({"status": "ok", "message": "Registro eliminado."})
    except ValueError as e:
        return _master_error(e)


@datos_bp.patch("/master/<name>/<row_id>/status")
@login_required
@permission_required("masters.write")
def master_status(name: str, row_id: str):
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("active"), bool):
        return jsonify({"status": "error", "message": "Indique un estado válido.", "code": "invalid_active"}), 400
    try:
        row = services.set_row_active(name, row_id, body["active"])
        label = "habilitado" if body["active"] else "inhabilitado"
        return jsonify({"status": "ok", "message": f"Registro {label}.", "row": row})
    except ValueError as e:
        return _master_error(e)


@datos_bp.post("/master/dim_producto/<int:product_id>/image")
@login_required
@permission_required("masters.write")
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
@login_required
@permission_required("elt.run")
def build_model():
    try:
        stats = services.run_build_model()
        return jsonify({"status": "ok", "message": "Modelo reconstruido.", **stats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@datos_bp.post("/load_dataset")
@login_required
@permission_required("elt.run")
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
@permission_required("audit.read")
def audit_log():
    try:
        role = (request.args.get("role") or "").strip() or None
        entity = (request.args.get("entity") or "").strip() or None
        entity_id = (request.args.get("entity_id") or "").strip() or None
        data = services.list_audit_log(
            limit=min(int(request.args.get("limit", 100)), 100),
            offset=max(int(request.args.get("offset", 0)), 0),
            role=role,
            entity=entity,
            entity_id=entity_id,
            email=(request.args.get("email") or "").strip() or None,
            action=(request.args.get("action") or "").strip() or None,
            module=(request.args.get("module") or "").strip() or None,
            date_from=(request.args.get("date_from") or "").strip() or None,
            date_to=(request.args.get("date_to") or "").strip() or None,
        )
        return jsonify({"status": "ok", **data})
    except Exception as e:
        return jsonify(
            {"status": "error", "message": str(e), "code": "audit_error"}
        ), 500


@datos_bp.get("/audit_log/export")
@login_required
@permission_required("audit.read")
def audit_log_export():
    """Exporta la auditoría en PDF aplicando los mismos filtros de pantalla."""
    filters = {
        "role": (request.args.get("role") or "").strip() or None,
        "entity": (request.args.get("entity") or "").strip() or None,
        "email": (request.args.get("email") or "").strip() or None,
        "action": (request.args.get("action") or "").strip() or None,
        "module": (request.args.get("module") or "").strip() or None,
        "date_from": (request.args.get("date_from") or "").strip() or None,
        "date_to": (request.args.get("date_to") or "").strip() or None,
    }
    entries: list[dict] = []
    for offset in range(0, 5000, 100):
        page = services.list_audit_log(limit=100, offset=offset, **filters)
        entries.extend(page["entries"])
        if len(entries) >= page["total"] or not page["entries"]:
            break
    action_names = {
        "export": "Exportó un informe", "update_profile": "Actualizó su perfil",
        "product_sale_toggle": "Cambió una rebaja", "category_sale_toggle": "Cambió rebaja de categoría",
        "create_request": "Creó una solicitud", "issue_invoice": "Generó una factura",
        "shop_sync": "Sincronizó la tienda", "enable": "Habilitó un registro", "disable": "Inhabilitó un registro",
    }
    def local_time(value):
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(ZoneInfo("America/Guayaquil")).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            return str(value or "-")
    pdf_rows = [{
        "fecha": local_time(row.get("at")), "modulo": row.get("module"), "accion": action_names.get(row.get("action"), str(row.get("action") or "").replace("_", " ").capitalize()),
        "entidad": row.get("entity"), "referencia": row.get("entity_id"),
        "usuario": row.get("email"), "rol": row.get("role"),
        "cambios": str(row.get("changes") or row.get("details") or {}),
    } for row in entries]
    columns = ["fecha", "modulo", "accion", "entidad", "referencia", "usuario", "rol", "cambios"]
    pdf = generate_report_pdf(
        report_id="AUDITORIA", title="Registro de auditoría",
        subtitle="Historial de acciones administrativas con los filtros aplicados.",
        columns=columns, rows=pdf_rows, total=len(pdf_rows),
    )
    log_audit("export", entity="audit_log", details={"rows": len(entries), "filters": filters, "format": "pdf"})
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="altavia-trade-auditoria.pdf"'},
    )


@datos_bp.get("/schema")
def schema_summary():
    return jsonify({"status": "ok", "tables": services.list_tables()})


@datos_bp.get("/meta/data-layers")
def meta_data_layers():
    """Capas operativo / landing / estratégico."""
    from shared.data_layers import layers_overview

    return jsonify({"status": "ok", **layers_overview()})


@datos_bp.post("/analytics/sync-order")
@login_required
@permission_required("elt.run")
def analytics_sync_order():
    from shared.analytics_sync import sync_order_to_fact

    body = request.get_json(silent=True) or {}
    order_id = body.get("order_id") or request.args.get("order_id")
    if not order_id:
        return jsonify({"status": "error", "message": "order_id requerido."}), 400
    try:
        result = sync_order_to_fact(order_id)
        return jsonify({"status": "ok", **result})
    except ValueError as e:
        if str(e) == "order_not_in_landing":
            return jsonify({"status": "error", "message": "Pedido no está en sales_records."}), 404
        raise
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@datos_bp.post("/analytics/sync-stale")
@login_required
@permission_required("elt.run")
def analytics_sync_stale():
    from shared.analytics_sync import sync_stale_orders

    body = request.get_json(silent=True) or {}
    limit = min(int(body.get("limit") or request.args.get("limit") or 50), 200)
    try:
        result = sync_stale_orders(limit=limit)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _master_error(exc: ValueError):
    code = str(exc)
    messages = {
        "unknown_table": ("Tabla maestra no encontrada.", 404),
        "read_only": ("Esta tabla es solo lectura.", 403),
        "fixed_catalog": ("Este es un catálogo fijo: puede editar o inhabilitar sus registros, pero no agregar nuevos.", 403),
        "not_found": ("Registro no encontrado.", 404),
        "duplicate_pk": ("Ya existe un registro con ese identificador.", 409),
        "duplicate_value": ("Ya existe un registro con ese nombre, código o correo.", 409),
        "has_children": ("No se puede eliminar: hay registros relacionados.", 409),
        "has_history": ("No se puede eliminar porque el registro tiene historial. Inhabilítelo en su lugar.", 409),
        "invalid_image_type": ("Formato no permitido. Use JPG, PNG o WEBP.", 400),
        "image_too_large": ("Imagen demasiado grande.", 400),
        "invalid_field": ("Revisa los campos: IDs y precios deben ser números positivos.", 400),
        "inactive_relation": ("El registro relacionado está inhabilitado o no existe.", 409),
    }
    msg, status = messages.get(code, (code, 400))
    return jsonify({"status": "error", "message": msg, "code": code}), status
