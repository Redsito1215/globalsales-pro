# -*- coding: utf-8 -*-
"""Alertas proactivas de stock bajo (notificaciones in-app)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

DEFAULT_LOW_STOCK_THRESHOLD = 20


def maybe_notify_low_stock(
    db,
    variant_id: int,
    *,
    threshold: int = DEFAULT_LOW_STOCK_THRESHOLD,
    reason: str = "stock_change",
) -> bool:
    """Notifica a compras si el SKU queda en o bajo umbral. Máx. una alerta por SKU y día."""
    vid = int(variant_id)
    variant = db["product_variants"].find_one({"variant_id": vid}, {"_id": 0})
    if not variant:
        return False

    threshold = int(variant.get("minimum_stock") if variant.get("minimum_stock") is not None else threshold)
    qty = int(variant.get("inventory_quantity") or 0)
    meta_id = f"low_stock_alert_{vid}"
    if qty > int(threshold):
        db["app_meta"].delete_one({"_id": meta_id})
        return False

    today = date.today().isoformat()
    existing = db["app_meta"].find_one({"_id": meta_id}, {"alerted_at": 1})
    if existing and existing.get("alerted_at") == today:
        return False

    pid = variant.get("product_id")
    prod = db["products"].find_one({"product_id": pid}, {"_id": 0, "title": 1, "name": 1}) if pid else None
    title = str((prod or {}).get("title") or (prod or {}).get("name") or f"Producto {pid or vid}")
    sku = str(variant.get("sku") or "").strip()

    from shared.notifications import notify_roles
    from shared.roles_registry import ADMIN_ROLE, VENDEDOR_ROLE

    label = f"{sku} — {title}" if sku else title
    notify_roles(
        roles=(ADMIN_ROLE, VENDEDOR_ROLE),
        subject=f"Stock bajo: {label}",
        body=(
            f"Quedan {qty} unidad(es) de {label} (umbral ≤ {threshold}).\n"
            f"Revisa Compras e inventario para reponer o crear una OC a proveedor."
        ),
        category="compras",
        meta={
            "variant_id": vid,
            "product_id": pid,
            "sku": sku or None,
            "qty": qty,
            "threshold": int(threshold),
            "reason": reason,
        },
    )
    db["app_meta"].update_one(
        {"_id": meta_id},
        {
            "$set": {
                "alerted_at": today,
                "qty": qty,
                "threshold": int(threshold),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )
    return True
