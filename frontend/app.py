"""GLOBTRADE S.A. — Plataforma web (Q1–Q4)."""
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from flask import Flask, redirect, request, send_from_directory, session
from flask_cors import CORS

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

static_dir = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(static_dir))
app.secret_key = settings.flask_secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=settings.session_days)
app.config["MAX_CONTENT_LENGTH"] = settings.max_product_image_mb * 1024 * 1024

CORS(app, supports_credentials=True)

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


@app.after_request
def _security_and_cache_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    path = request.path or ""
    if path.startswith("/static/") and (
        path.endswith(".js") or path.endswith(".css") or path.endswith(".html")
    ):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


def _sem1_admin_only():
    if session.get("role") != "administrador":
        return redirect("/")


@app.route("/sem1")
@app.route("/sem1/")
def sem1_dashboard():
    denied = _sem1_admin_only()
    if denied:
        return denied
    return send_from_directory(Path(app.static_folder) / "sem1", "index.html")


@app.route("/sem1/master")
def sem1_master_tables():
    denied = _sem1_admin_only()
    if denied:
        return denied
    return send_from_directory(Path(app.static_folder) / "sem1", "master_tables.html")


if __name__ == "__main__":
    port = settings.web_port
    debug = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes", "on")
    from shared.mongo import mongo_topology

    topo = mongo_topology()
    print(f"GLOBTRADE S.A. → http://127.0.0.1:{port}")
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
