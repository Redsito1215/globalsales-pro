"""GLOBTRADE S.A. — Plataforma web (Q1–Q4)."""
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from flask import Flask, redirect, send_from_directory, session
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


_init_auth()
_init_ops_indexes()
_init_uploads()


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
    print(f"GLOBTRADE S.A. → http://127.0.0.1:{port}")
    print(f"MongoDB: {settings.mongo_uri} / {settings.mongo_db}")
    app.run(host="0.0.0.0", debug=False, port=port)
