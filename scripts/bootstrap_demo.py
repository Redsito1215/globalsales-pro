#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bootstrap completo para demo GLOBTRADE (idempotente).

Uso:
  python scripts/bootstrap_demo.py
  python scripts/bootstrap_demo.py --skip-load
  python scripts/bootstrap_demo.py --force-users
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))


def _step(msg: str) -> None:
    print(f"\n==> {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap demo GLOBTRADE")
    parser.add_argument("--password", default="Demo1234!", help="Contraseña usuarios demo")
    parser.add_argument("--force-users", action="store_true", help="Recrear usuarios demo")
    parser.add_argument("--skip-load", action="store_true", help="No cargar CSV histórico")
    parser.add_argument("--skip-scenarios", action="store_true", help="No crear escenarios operativos")
    args = parser.parse_args()

    print("GLOBTRADE — bootstrap demo")
    try:
        from shared.mongo import get_db

        db = get_db()
    except Exception as exc:
        print(f"Error MongoDB: {exc}", file=sys.stderr)
        return 1

    _step("Usuarios demo")
    from scripts.seed_demo import seed_users

    seed_users(args.password, args.force_users)

    if not args.skip_load:
        sales_n = db["sales_records"].estimated_document_count()
        fact_n = db["fact_ventas"].estimated_document_count()
        if sales_n == 0:
            _step("Carga dataset histórico (CSV)")
            from paquetes.datos.services import run_load_dataset

            stats = run_load_dataset()
            print(f"   sales_records: {stats.get('sales_records')}, fact_ventas: {stats.get('fact_ventas')}")
        elif fact_n == 0:
            _step("Construir modelo estratégico")
            from paquetes.datos.services import run_build_model

            stats = run_build_model()
            print(f"   fact_ventas: {stats.get('fact_ventas')}")

    _step("Sincronizar catálogo tienda")
    from paquetes.shop.services import sync_from_masters

    counts = sync_from_masters(reset_stock=False)
    print(f"   productos: {counts.get('products', 0)}, variantes: {counts.get('product_variants', 0)}")

    _step("Proveedores demo")
    from scripts.seed_scenarios import ensure_demo_vendors

    n_v = ensure_demo_vendors()
    print(f"   proveedores nuevos: {n_v}")

    if not args.skip_scenarios:
        _step("Escenarios operativos")
        from scripts.seed_scenarios import seed_operational_scenarios

        created = seed_operational_scenarios()
        if created.get("skipped"):
            print("   ya existían — omitido")
        else:
            print(f"   {created}")

    _step("Índices operativos")
    from shared.ops_indexes import ensure_ops_indexes

    idx = ensure_ops_indexes()
    print(f"   colecciones indexadas: {len(idx)}")

    print("\n[OK] Bootstrap listo.")
    print("  Inicia sesión: admin@globtrade.demo /", args.password)
    print("  Cliente demo:  cliente@globtrade.demo /", args.password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
