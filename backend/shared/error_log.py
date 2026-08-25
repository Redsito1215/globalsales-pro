"""Registro central de errores sin exponer datos sensibles al cliente."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.mongo import get_db


def safe_error_summary(exc: BaseException) -> str:
    name = type(exc).__name__
    message = str(exc).replace("\n", " ").replace("\r", " ")[:300]
    return f"{name}: {message}" if message else name


def record_error(
    exc: BaseException, *, path: str | None = None, method: str | None = None,
    actor_email: str | None = None, context: dict[str, Any] | None = None,
) -> None:
    try:
        get_db()["system_errors"].insert_one({
            "error_type": type(exc).__name__, "summary": safe_error_summary(exc),
            "path": path, "method": method, "actor_email": actor_email,
            "context": context or {}, "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
    except Exception:
        pass

