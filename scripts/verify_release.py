"""Verificación de preparación de GLOBTRADE, sin modificar datos."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


def check(name: str, ok: bool, detail: str) -> dict[str, str | bool]:
    return {"check": name, "ok": bool(ok), "detail": detail}


def run(*, skip_mongo: bool = False) -> dict:
    results: list[dict[str, str | bool]] = []
    required = [
        "frontend/app.py", "frontend/static/index.html", "requirements.txt",
        "docs/manual-operacion.md", "docs/plan-de-pruebas.md",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    results.append(check("archivos", not missing, "completos" if not missing else f"faltan: {', '.join(missing)}"))

    try:
        from frontend.app import app

        client = app.test_client()
        home = client.get("/")
        results.append(check("aplicacion", home.status_code == 200, f"GET /: HTTP {home.status_code}"))
        health = client.get("/api/health")
        results.append(check("salud", health.status_code == 200, f"GET /api/health: HTTP {health.status_code}"))
    except Exception as exc:  # pragma: no cover - diagnóstico operativo
        results.append(check("aplicacion", False, f"{type(exc).__name__}: {exc}"))

    if skip_mongo:
        results.append(check("mongo", True, "omitido por parámetro"))
    else:
        try:
            from shared.mongo import get_dw_db, get_ops_db

            get_ops_db().command("ping")
            get_dw_db().command("ping")
            ops_count = len(get_ops_db().list_collection_names())
            dw_count = len(get_dw_db().list_collection_names())
            results.append(check("mongo", True, f"operativo={ops_count} colecciones; analítico={dw_count}"))
        except Exception as exc:  # pragma: no cover - depende del entorno
            results.append(check("mongo", False, f"{type(exc).__name__}: {exc}"))

    return {"ready": all(bool(item["ok"]) for item in results), "checks": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Comprueba archivos, aplicación y MongoDB sin escribir datos.")
    parser.add_argument("--skip-mongo", action="store_true", help="Omite la conexión a MongoDB.")
    args = parser.parse_args()
    report = run(skip_mongo=args.skip_mongo)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
