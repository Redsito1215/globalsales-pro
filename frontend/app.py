"""Altavia Trade — Plataforma web (Q1–Q4)."""
import os
import sys
import time
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from flask import Flask, g, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from auth import users as user_store
from auth.routes import auth_bp
from config.settings import settings
from paquetes.datos import datos_bp
from paquetes.analisis import analisis_bp
from paquetes.tablero import tablero_bp
from paquetes.ventas import ventas_bp
from paquetes.shop import shop_bp
from paquetes.soporte import soporte_bp
from paquetes.decisiones import decisiones_bp
from paquetes.compras import compras_bp
from paquetes.reportes import reportes_bp
from paquetes.empresa import empresa_bp
from paquetes.profesional import profesional_bp

static_dir = Path(__file__).parent / "static"
settings.assert_safe_production()

app = Flask(__name__, static_folder=str(static_dir))
app.secret_key = settings.flask_secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = settings.session_cookie_secure
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=settings.session_idle_minutes)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["MAX_CONTENT_LENGTH"] = settings.max_product_image_mb * 1024 * 1024

CORS(app, supports_credentials=True, origins=settings.allowed_cors_origins())

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(tablero_bp)
app.register_blueprint(analisis_bp)
app.register_blueprint(datos_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(shop_bp)
app.register_blueprint(soporte_bp)
app.register_blueprint(decisiones_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(empresa_bp)
app.register_blueprint(profesional_bp)

import paquetes.tablero.catalogo as _catalogo_mod

_catalogo_mod.invalidate_catalog_cache()


def _init_auth():
    try:
        user_store.ensure_indexes()
        from auth import roles_service
        roles_service.ensure_roles_seed()
    except Exception as e:
        print(f"[auth] índices usuarios/roles: {e}")


def _init_ops_indexes():
    try:
        from shared.ops_indexes import ensure_ops_indexes

        counts = ensure_ops_indexes()
        total = sum(counts.values())
        print(f"[ops] índices operativos asegurados: {total} en {len(counts)} colecciones")
    except Exception as e:
        print(f"[ops] índices operativos: {e}")


def _init_uploads():
    settings.product_uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.company_uploads_dir.mkdir(parents=True, exist_ok=True)


def _init_legacy_order_ids():
    try:
        from paquetes.ventas.services import repair_legacy_platform_order_ids

        fixed = repair_legacy_platform_order_ids()
        if fixed:
            print(f"[ventas] order_id legacy reparados: {fixed} pedido(s) (1000000000 → V-xxxxx)")
    except Exception as e:
        print(f"[ventas] reparación order_id legacy: {e}")


def _init_mongo_split():
    try:
        from shared.mongo_split import ensure_ops_split_bootstrap

        result = ensure_ops_split_bootstrap()
        if result.get("auto") and result.get("moved"):
            print(
                f"[mongo] split ops/DW: copiados {result['moved']} doc(s) "
                f"en {result['collections']} colección(es) → {result['ops_database']}"
            )
            print("[mongo] opcional: python scripts/migrate_split_mongo.py --drop-source")
    except Exception as e:
        print(f"[mongo] bootstrap split ops/DW: {e}")


_init_auth()
_init_ops_indexes()
_init_uploads()
_init_legacy_order_ids()
_init_mongo_split()


@app.before_request
def _request_context():
    g.request_started = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex


@app.after_request
def _security_and_cache_headers(resp):
    resp.headers["X-Request-ID"] = getattr(g, "request_id", "")
    started = getattr(g, "request_started", None)
    if started is not None:
        resp.headers["Server-Timing"] = f"app;dur={(time.perf_counter() - started) * 1000:.1f}"
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'")
    resp.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    if settings.session_cookie_secure:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    path = request.path or ""
    if path == "/" or path.endswith(".html") or (
        path.startswith("/static/")
        and (path.endswith(".js") or path.endswith(".css") or path.endswith(".html"))
    ):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@app.errorhandler(Exception)
def _handle_unexpected_error(exc):
    if isinstance(exc, HTTPException):
        return exc
    from shared.error_log import record_error

    record_error(
        exc, path=request.path, method=request.method,
        actor_email=session.get("email"), context={"request_id": getattr(g, "request_id", None)},
    )
    return jsonify({
        "status": "error", "message": "Ocurrió un error interno. Intenta nuevamente.",
        "code": "internal_error", "request_id": getattr(g, "request_id", None),
    }), 500


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = settings.web_port
    debug = settings.app_env.lower() != "production" and os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes", "on")
    from shared.mongo import mongo_topology

    topo = mongo_topology()
    print(f"Altavia Trade → http://127.0.0.1:{port}")
    if topo["split_enabled"]:
        print(
            f"MongoDB ops: {topo['mongo_uri']} / {topo['ops_database']} · "
            f"DW: {topo['dw_database']}"
        )
    else:
        print(f"MongoDB: {topo['mongo_uri']} / {topo['dw_database']} (base única)")
    if topo["replica_reads"]:
        print(f"MongoDB lecturas analíticas: réplica {topo['replica_uri']}")
    if debug:
        print("[web] FLASK_DEBUG=1 — recarga automática de Python")
    app.run(host="0.0.0.0", debug=debug, use_reloader=debug, port=port)
