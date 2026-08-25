# -*- coding: utf-8 -*-
"""Consultas de reportes simples (capa operativa / OLTP)."""
from __future__ import annotations

from typing import Any, Callable

from shared.mongo import get_db

from paquetes.reportes.catalog import REPORT_BY_ID, REPORTS


def list_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "objetivo": r["objetivo"],
            "para_que": r["para_que"],
            "quien": r["quien"],
            "tipo": "simple",
            "columns": r["columns"],
        }
        for r in REPORTS
    ]


def _search_match(row: dict[str, Any], q: str | None, fields: list[str]) -> bool:
    if not q:
        return True
    needle = q.strip().lower()
    if not needle:
        return True
    for f in fields:
        val = row.get(f)
        if val is not None and needle in str(val).lower():
            return True
    return False


def rs01(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_requests"]
        .find({"status": {"$in": ["pendiente", "en_revision"]}}, {"_id": 0})
        .sort("created_at", 1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        row = {
            "request_id": r.get("request_id"),
            "client_name": r.get("client_name") or r.get("customer_name") or "",
            "client_email": r.get("client_email") or "",
            "status": r.get("status"),
            "payment_status": r.get("payment_status") or "pendiente_pago",
            "total": r.get("total") or r.get("total_amount") or 0,
            "created_at": r.get("created_at"),
        }
        if _search_match(row, q, ["request_id", "client_name", "client_email"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs02(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_requests"]
        .find({"payment_status": {"$in": ["pendiente_pago", "credito"]}}, {"_id": 0})
        .sort("created_at", 1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        row = {
            "request_id": r.get("request_id"),
            "client_name": r.get("client_name") or "",
            "payment_status": r.get("payment_status"),
            "total": r.get("total") or r.get("total_amount") or 0,
            "status": r.get("status"),
            "created_at": r.get("created_at"),
        }
        if _search_match(row, q, ["request_id", "client_name", "payment_status"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs03(*, q: str | None = None, threshold: int = 20, limit: int = 100) -> dict[str, Any]:
    from paquetes.compras import services as compras

    data = compras.list_inventory(q=q, low_only=True, threshold=threshold, limit=limit, offset=0)
    rows = [
        {
            "sku": i.get("sku"),
            "product_name": i.get("title") or i.get("product_name") or i.get("name"),
            "inventory_quantity": i.get("inventory_quantity"),
            "unit_price": i.get("price") or i.get("unit_price"),
            "unit_cost": i.get("cost") or i.get("unit_cost"),
            "vendor_name": i.get("vendor") or i.get("vendor_name") or "",
        }
        for i in data.get("items") or []
    ]
    return {"rows": rows, "total": data.get("total", len(rows)), "threshold": threshold}


def rs04(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    pipe = [
        {"$sort": {"created_at": 1, "message_id": 1}},
        {
            "$group": {
                "_id": "$thread_email",
                "last_body": {"$last": "$text"},
                "last_at": {"$last": "$created_at"},
                "last_staff": {"$last": "$staff"},
                "message_count": {"$sum": 1},
            }
        },
        {"$match": {"last_staff": {"$ne": True}}},
        {"$sort": {"last_at": -1}},
        {"$limit": limit * 2},
    ]
    rows = list(db["support_messages"].aggregate(pipe))
    out = []
    for r in rows:
        row = {
            "thread_email": r.get("_id"),
            "last_body": (r.get("last_body") or "")[:160],
            "last_at": r.get("last_at"),
            "message_count": r.get("message_count"),
            "espera_respuesta": True,
        }
        if _search_match(row, q, ["thread_email", "last_body"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs05(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_orders"]
        .find({"status": {"$in": ["enviada", "parcial"]}}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        vendor = db["vendors"].find_one({"vendor_id": r.get("vendor_id")}, {"_id": 0, "name": 1})
        row = {
            "po_id": r.get("po_id"),
            "vendor_name": (vendor or {}).get("name") or r.get("vendor_name") or "",
            "status": r.get("status"),
            "created_at": r.get("created_at"),
            "received_at": r.get("received_at"),
            "notes": r.get("notes") or "",
        }
        if _search_match(row, q, ["po_id", "vendor_name", "status"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs06(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(db["vendors"].find({"active": {"$ne": False}}, {"_id": 0}).sort("name", 1).limit(limit * 2))
    out = []
    for r in rows:
        row = {
            "vendor_id": r.get("vendor_id"),
            "name": r.get("name"),
            "country": r.get("country") or "",
            "email": r.get("email") or "",
            "phone": r.get("phone") or "",
            "active": bool(r.get("active", True)),
        }
        if _search_match(row, q, ["name", "email", "country", "vendor_id"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs07(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_requests"]
        .find(
            {
                "status": "convertida",
                "$or": [{"shipped_at": None}, {"shipped_at": {"$exists": False}}, {"shipped_at": ""}],
            },
            {"_id": 0},
        )
        .sort("created_at", 1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        row = {
            "request_id": r.get("request_id"),
            "client_name": r.get("client_name") or "",
            "order_id": r.get("order_id"),
            "total": r.get("total") or r.get("total_amount") or 0,
            "created_at": r.get("created_at"),
        }
        if _search_match(row, q, ["request_id", "order_id", "client_name"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs08(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_requests"]
        .find({"status": "enviada"}, {"_id": 0})
        .sort("shipped_at", 1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        row = {
            "request_id": r.get("request_id"),
            "client_name": r.get("client_name") or "",
            "tracking": r.get("tracking") or r.get("tracking_code") or r.get("order_id") or "",
            "shipped_at": r.get("shipped_at"),
            "total": r.get("total") or r.get("total_amount") or 0,
        }
        if _search_match(row, q, ["request_id", "tracking", "client_name"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs09(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(db["discount_codes"].find({"active": {"$ne": False}}, {"_id": 0}).sort("code", 1).limit(limit * 2))
    out = []
    for r in rows:
        row = {
            "code": r.get("code"),
            "discount_type": r.get("type") or r.get("discount_type") or "",
            "value": r.get("value") or r.get("amount") or 0,
            "uses": r.get("uses") or r.get("used_count") or 0,
            "max_uses": r.get("max_uses") or r.get("usage_limit"),
            "active": bool(r.get("active", True)),
        }
        if _search_match(row, q, ["code", "discount_type"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs10(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(db["users"].find({}, {"_id": 0, "password_hash": 0}).sort("name", 1).limit(limit * 2))
    out = []
    for r in rows:
        row = {
            "name": r.get("name") or "",
            "email": r.get("email") or "",
            "role": r.get("role") or "",
            "active": bool(r.get("active", True)),
        }
        if _search_match(row, q, ["name", "email", "role"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs11(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    products = list(db["products"].find({}, {"_id": 0}).sort("title", 1).limit(limit * 2))
    out = []
    for p in products:
        pid = p.get("product_id")
        variant = db["product_variants"].find_one({"product_id": pid}, {"_id": 0}) or {}
        cat = ""
        cp = db["collection_products"].find_one({"product_id": pid}, {"_id": 0})
        if cp:
            col = db["collections"].find_one({"collection_id": cp.get("collection_id")}, {"_id": 0, "title": 1})
            cat = (col or {}).get("title") or ""
        row = {
            "product_name": p.get("title") or p.get("name") or "",
            "category": cat,
            "sku": variant.get("sku") or "",
            "unit_price": variant.get("price") or p.get("price") or 0,
            "inventory_quantity": variant.get("inventory_quantity") or 0,
            "status": "activo" if p.get("published", True) else "inactivo",
        }
        if _search_match(row, q, ["product_name", "sku", "category"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs12(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    db = get_db()
    rows = list(
        db["purchase_requests"]
        .find({"reviewed_by": {"$nin": [None, ""]}}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit * 2)
    )
    out = []
    for r in rows:
        row = {
            "request_id": r.get("request_id"),
            "client_name": r.get("client_name") or "",
            "status": r.get("status"),
            "reviewed_by": r.get("reviewed_by"),
            "created_at": r.get("created_at"),
            "total": r.get("total") or r.get("total_amount") or 0,
        }
        if _search_match(row, q, ["request_id", "client_name", "reviewed_by", "status"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out)}


def rs13(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    from shared.cash_ledger import list_cash_movements

    data = list_cash_movements(limit=limit, q=q)
    rows = []
    type_labels = {"payment_in": "Entrada (pago)", "refund_out": "Salida (devolución)", "adjustment": "Ajuste"}
    for m in data.get("movements") or []:
        row = {
            "movement_id": m.get("movement_id"),
            "created_at": (m.get("created_at") or "")[:10],
            "movement_type": type_labels.get(m.get("movement_type"), m.get("movement_type")),
            "amount": m.get("amount"),
            "request_id": m.get("request_id"),
            "order_id": m.get("order_id"),
            "reference": m.get("reference"),
        }
        if _search_match(row, q, ["reference", "order_id", "movement_type"]):
            rows.append(row)
    return {"rows": rows[:limit], "total": len(rows), "summary": data.get("summary")}


def rs14(*, q: str | None = None, limit: int = 100) -> dict[str, Any]:
    from shared.cash_ledger import list_cash_movements

    db = get_db()
    cash = list_cash_movements(limit=500)
    summary = cash.get("summary") or {}
    returns = db["purchase_requests"].count_documents({"status": "devuelta"})
    refund_amount = round(float(summary.get("total_out") or 0), 2)
    rows = [
        {"concepto": "Pagos recibidos", "monto": summary.get("total_in", 0), "cantidad": cash.get("summary", {}).get("count", 0), "periodo": "acumulado"},
        {"concepto": "Reembolsos / devoluciones", "monto": refund_amount, "cantidad": returns, "periodo": "acumulado"},
        {"concepto": "Neto caja", "monto": summary.get("net", 0), "cantidad": "—", "periodo": "acumulado"},
    ]
    out = [r for r in rows if _search_match(r, q, ["concepto", "periodo"])]
    return {"rows": out[:limit], "total": len(out)}


def rs15(*, q: str | None = None, limit: int = 100, threshold: int = 20) -> dict[str, Any]:
    db = get_db()
    variants = list(db["product_variants"].find({}, {"_id": 0}).sort("sku", 1).limit(limit * 2))
    out = []
    total_value = 0.0
    for v in variants:
        qty = int(v.get("inventory_quantity") or 0)
        cost = float(v.get("cost") or 0)
        value = round(qty * cost, 2)
        total_value += value
        prod = db["products"].find_one({"product_id": v.get("product_id")}, {"_id": 0, "title": 1})
        row = {
            "sku": v.get("sku") or "",
            "product_name": (prod or {}).get("title") or f"Producto {v.get('product_id')}",
            "inventory_quantity": qty,
            "unit_cost": round(cost, 2),
            "stock_value": value,
        }
        if _search_match(row, q, ["sku", "product_name"]):
            out.append(row)
    return {"rows": out[:limit], "total": len(out), "total_stock_value": round(total_value, 2)}


_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "RS-01": rs01,
    "RS-02": rs02,
    "RS-03": rs03,
    "RS-04": rs04,
    "RS-05": rs05,
    "RS-06": rs06,
    "RS-07": rs07,
    "RS-08": rs08,
    "RS-09": rs09,
    "RS-10": rs10,
    "RS-11": rs11,
    "RS-12": rs12,
    "RS-13": rs13,
    "RS-14": rs14,
    "RS-15": rs15,
}


def run_report(report_id: str, *, q: str | None = None, limit: int = 100, threshold: int = 20) -> dict[str, Any]:
    rid = (report_id or "").strip().upper()
    meta = REPORT_BY_ID.get(rid)
    if not meta:
        raise ValueError("unknown_report")
    runner = _RUNNERS[rid]
    if rid == "RS-03":
        data = runner(q=q, threshold=threshold, limit=limit)
    elif rid == "RS-15":
        data = runner(q=q, threshold=threshold, limit=limit)
    else:
        data = runner(q=q, limit=limit)
    return {
        "report": {
            "id": meta["id"],
            "name": meta["name"],
            "objetivo": meta["objetivo"],
            "para_que": meta["para_que"],
            "quien": meta["quien"],
            "tipo": "simple",
            "columns": meta["columns"],
            "data_layer": "operativo",
        },
        **data,
    }
