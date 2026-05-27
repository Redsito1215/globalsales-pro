"""Dashboard web GLOBTRADE — puerto 5000, datos desde MongoDB."""
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
import mongo_manager as db
from auth.routes import auth_bp
from auth.decorators import admin_required
from auth import users as user_store
from config.settings import settings

static_dir = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=str(static_dir))
app.secret_key = settings.flask_secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=settings.session_days)

CORS(app, supports_credentials=True, origins=[
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    f"http://127.0.0.1:{settings.web_port}",
    f"http://localhost:{settings.web_port}",
])

app.register_blueprint(auth_bp, url_prefix="/api/auth")


@app.before_request
def _make_session_permanent():
    session.permanent = True


def _init_auth():
    try:
        user_store.ensure_indexes()
    except Exception as e:
        print(f"[auth] No se pudo inicializar índices de usuarios: {e}")


_init_auth()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/master")
def master_tables():
    return send_from_directory(app.static_folder, "master_tables.html")


@app.get("/api/health")
def health():
    try:
        db._db().command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return jsonify({
        "status": "ok" if mongo_ok else "degraded",
        "mongo": mongo_ok,
        "authenticated": bool(session.get("user_id")),
    })


@app.route("/api/summary")
def summary():
    return jsonify(db.get_summary())


@app.route("/api/regions")
def regions():
    return jsonify(db.revenue_by_region())


@app.route("/api/products")
def products():
    return jsonify(db.revenue_by_product())


@app.route("/api/trend")
def trend():
    return jsonify(list(reversed(db.monthly_trend(int(request.args.get("months", 24))))))


@app.route("/api/channels")
def channels():
    return jsonify(db.channel_breakdown())


@app.route("/api/priorities")
def priorities():
    return jsonify(db.priority_breakdown())


@app.route("/api/countries")
def countries():
    return jsonify(db.top_countries(int(request.args.get("top", 10))))


@app.route("/api/orders")
def orders():
    return jsonify(db.search_orders(
        country=request.args.get("country"),
        item_type=request.args.get("item_type"),
        channel=request.args.get("channel"),
        priority=request.args.get("priority"),
        limit=int(request.args.get("limit", 50)),
        offset=int(request.args.get("offset", 0)),
    ))


@app.route("/api/orders/count")
def orders_count():
    return jsonify({"total": db.count_orders(
        country=request.args.get("country"),
        item_type=request.args.get("item_type"),
        channel=request.args.get("channel"),
        priority=request.args.get("priority"),
    )})


@app.route("/api/orders/<order_id>")
def get_order(order_id):
    row = db.get_order(order_id)
    if not row:
        return jsonify({"status": "error", "message": "No encontrado"}), 404
    return jsonify(row)


@app.route("/api/elt_status")
def elt_status():
    pq = settings.data_parquet_dir / "sales_records.parquet"
    return jsonify({
        "parquet": str(pq),
        "parquet_exists": pq.exists(),
        "mongo_db": settings.mongo_db,
    })


@app.get("/api/master/tables")
def master_tables_list():
    return jsonify(db.master_tables())


@app.get("/api/master/<name>")
def master_browse(name: str):
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    q = request.args.get("q") or ""
    return jsonify(db.master_browse(name=name, limit=limit, offset=offset, q=q))


@app.post("/api/build_model")
@admin_required
def build_model():
    try:
        from etl.transform_fact_dimensions import main as build_main

        build_main(mongo_uri=settings.mongo_uri, mongo_db=settings.mongo_db)
        return jsonify({"status": "ok", "message": "Tablas maestras construidas."})
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 1)
        return jsonify({"status": "error", "message": "No se pudo construir el modelo (sales_records vacío)."}), 400 if code == 1 else 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.post("/api/load_dataset")
@admin_required
def load_dataset():
    """Ejecuta ELT completo: CSV → Parquet → MongoDB → dimensiones."""
    import subprocess

    body = request.get_json(silent=True) or {}
    csv_path = (body.get("csv_path") or "").strip()
    if csv_path:
        settings.csv_source = Path(csv_path) if Path(csv_path).is_absolute() else ROOT / csv_path

    if not settings.csv_source.exists():
        return jsonify({
            "status": "error",
            "message": f"No se encontró el CSV: {settings.csv_source}",
        }), 400

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "etl.run_pipeline_mongo"],
            cwd=str(ROOT / "backend"),
            capture_output=True,
            text=True,
            timeout=600,
            env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "backend")},
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-800:]
            return jsonify({"status": "error", "message": f"ELT falló.\n{tail}"}), 500
        return jsonify({
            "status": "ok",
            "message": "Dataset cargado y modelo dimensional actualizado.",
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "La carga excedió el tiempo máximo (10 min)."}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print(f"GLOBTRADE dashboard → http://0.0.0.0:{settings.web_port}")
    print(f"Parquet en: {settings.data_parquet_dir}")
    app.run(host="0.0.0.0", debug=False, port=settings.web_port)
