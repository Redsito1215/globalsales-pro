"""Registro seguro de intentos de pago con tarjeta."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ALLOWED_OUTCOMES = frozenset({"approved", "declined", "insufficient_funds", "invalid_card"})


def sanitize_card_metadata(data: dict[str, Any] | None) -> dict[str, Any]:
    raw = data or {}
    forbidden = {"cvv", "cvc", "pan", "card_number", "number"}
    if forbidden.intersection(raw):
        raise ValueError("sensitive_card_data")
    last4 = "".join(ch for ch in str(raw.get("last4") or "") if ch.isdigit())
    if len(last4) != 4:
        raise ValueError("invalid_card_metadata")
    brand = str(raw.get("brand") or "TARJETA").strip().upper()[:20]
    exp_month = int(raw.get("exp_month") or 0)
    exp_year = int(raw.get("exp_year") or 0)
    if not 1 <= exp_month <= 12 or exp_year < 2000:
        raise ValueError("invalid_card_metadata")
    return {"brand": brand, "last4": last4, "exp_month": exp_month, "exp_year": exp_year}


def record_payment_attempt(
    db: Any, *, request_id: int, amount: float, outcome: str, idempotency_key: str,
    card: dict[str, Any], actor_email: str | None = None, failure_code: str | None = None,
) -> tuple[dict[str, Any], bool]:
    key = str(idempotency_key or "").strip()[:120]
    if len(key) < 12:
        raise ValueError("invalid_idempotency_key")
    existing = db["payment_attempts"].find_one({"idempotency_key": key}, {"_id": 0})
    if existing:
        if int(existing.get("request_id") or 0) != int(request_id):
            raise ValueError("duplicate_payment_attempt")
        return existing, False
    status = str(outcome or "").strip().lower()
    if status not in ALLOWED_OUTCOMES:
        raise ValueError("invalid_payment_outcome")
    safe_card = sanitize_card_metadata(card)
    counter = db["app_meta"].find_one_and_update(
        {"_id": "payment_attempt_id"}, {"$inc": {"value": 1}}, upsert=True, return_document=True,
    )
    attempt_id = int((counter or {}).get("value") or 1)
    doc = {
        "attempt_id": attempt_id, "transaction_reference": f"PAY-{attempt_id:08d}",
        "idempotency_key": key, "request_id": int(request_id), "amount": round(float(amount or 0), 2),
        "currency": "USD", "outcome": status, "failure_code": failure_code,
        "payment_method": "tarjeta", "card": safe_card, "actor_email": actor_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db["payment_attempts"].insert_one(doc)
    doc.pop("_id", None)
    return doc, True

