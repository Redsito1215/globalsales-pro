#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escenarios operativos de demo — idempotente (marca [DEMO])."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

DEMO_TAG = "[DEMO]"


def _db():
    from shared.mongo import get_db

    return get_db()


def ensure_demo_vendors() -> int:
    """Crea proveedores demo si no hay ninguno."""
    db = _db()
    if db["vendors"].count_documents({}) > 0:
        return 0
    from paquetes.compras.services import upsert_vendor

    pais = db["dim_pais"].find_one({"name": "Germany"}, {"_id": 0}) or db["dim_pais"].find_one({}, {"_id": 0})
    if not pais:
        return 0
    samples = [
        {"name": "Proveedor Europa", "email": "compras@europa.demo", "country_id": pais["country_id"]},
        {"name": "Suministros Global", "email": "ops@global.demo", "country_id": pais["country_id"]},
    ]
    for row in samples:
        upsert_vendor(row)
    return len(samples)


def seed_operational_scenarios() -> dict[str, int]:
    """Crea solicitudes/requisiciones/OC de ejemplo para recorrer la demo."""
    db = _db()
    if db["app_meta"].find_one({"_id": "demo_scenarios_seeded"}):
        return {"skipped": 1}

    created = {"requests": 0, "requisitions": 0, "pos": 0}

    variant = db["product_variants"].find_one({}, {"_id": 0, "variant_id": 1, "product_id": 1, "cost": 1})
    vendor = db["vendors"].find_one({"active": {"$ne": False}}, {"_id": 0, "vendor_id": 1})
    country = db["dim_pais"].find_one({"name": "Germany"}, {"_id": 0}) or db["dim_pais"].find_one({}, {"_id": 0})
    channel = db["dim_canal"].find_one({"name": "Online"}, {"_id": 0}) or db["dim_canal"].find_one({}, {"_id": 0})

    if variant and vendor and country and channel:
        from paquetes.compras import services as compras_svc

        try:
            req = compras_svc.create_purchase_requisition(
                {
                    "vendor_id": vendor["vendor_id"],
                    "notes": "Requisición de reposición",
                    "lines": [{"variant_id": variant["variant_id"], "quantity": 25, "unit_cost": variant.get("cost") or 1}],
                }
            )
            compras_svc.approve_purchase_requisition(int(req["req_id"]))
            created["requisitions"] += 1
        except ValueError:
            pass

        try:
            po = compras_svc.create_purchase_order(
                {
                    "vendor_id": vendor["vendor_id"],
                    "notes": "OC parcial",
                    "lines": [{"variant_id": variant["variant_id"], "quantity": 40, "unit_cost": variant.get("cost") or 1}],
                    "send": True,
                }
            )
            created["pos"] += 1
            if po.get("po_id"):
                lines = po.get("lines") or []
                if lines:
                    compras_svc.receive_purchase_order(
                        int(po["po_id"]),
                        receipts=[{"line_id": lines[0]["line_id"], "quantity": max(int(lines[0]["quantity_ordered"]) // 2, 1)}],
                    )
        except ValueError:
            pass

    client_email = "cliente@globtrade.demo"
    if country and channel and variant:
        prod = db["products"].find_one({"product_id": variant.get("product_id")}, {"_id": 0, "name": 1})
        pid = int(variant.get("product_id") or 0)
        rid = int((db["purchase_requests"].find_one({}, sort=[("request_id", -1)]) or {}).get("request_id") or 0) + 1
        total = round(float(variant.get("price") or 10) * 2, 2)
        db["purchase_requests"].insert_one(
            {
                "request_id": rid,
                "client_name": "Cliente",
                "client_email": client_email,
                "client_phone": None,
                "country_id": int(country["country_id"]),
                "channel_id": int(channel["channel_id"]),
                "status": "aprobada",
                "payment_status": "pendiente_pago",
                "paid_at": None,
                "paid_amount": None,
                "payment_due": total,
                "notes": "Pendiente de pago",
                "created_at": date.today().isoformat(),
                "reviewed_by": "admin@globtrade.demo",
                "order_id": None,
                "discount_amount": 0,
                "subtotal": total,
                "shipping_cost": 0,
                "total": total,
                "stock_lines": [{"variant_id": int(variant["variant_id"]), "quantity": 2, "product_id": pid}],
            }
        )
        lid = int((db["purchase_request_lines"].find_one({}, sort=[("line_id", -1)]) or {}).get("line_id") or 0) + 1
        db["purchase_request_lines"].insert_one(
            {
                "line_id": lid,
                "request_id": rid,
                "product_id": pid,
                "product_name": (prod or {}).get("title") or f"Producto {pid}",
                "quantity": 2,
                "unit_price": float(variant.get("price") or 10),
                "unit_cost": float(variant.get("cost") or 1),
                "line_gross": total,
                "discount_alloc": 0,
                "line_net": total,
            }
        )
        created["requests"] += 1

    db["app_meta"].update_one(
        {"_id": "demo_scenarios_seeded"},
        {"$set": {"seeded_at": date.today().isoformat(), "created": created}},
        upsert=True,
    )
    return created
