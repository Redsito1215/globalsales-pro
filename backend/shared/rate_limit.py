# -*- coding: utf-8 -*-
"""Rate limiting en memoria por IP (una instancia)."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import RLock

_buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
_lock = RLock()


def check_rate_limit(
    scope: str,
    key: str,
    *,
    max_attempts: int,
    window_sec: int,
) -> str | None:
    now = time.time()
    with _lock:
        bucket = _buckets[scope][key]
        bucket[:] = [t for t in bucket if now - t < window_sec]
        if len(bucket) >= max_attempts:
            mins = max(window_sec // 60, 1)
            return f"Demasiados intentos. Espera {mins} minuto(s) e inténtalo de nuevo."
    return None


def consume_attempt(scope: str, key: str, *, max_attempts: int, window_sec: int) -> str | None:
    """Comprueba y registra en una sola sección crítica para evitar carreras entre solicitudes."""
    now = time.time()
    with _lock:
        bucket = _buckets[scope][key]
        bucket[:] = [t for t in bucket if now - t < window_sec]
        if len(bucket) >= max_attempts:
            mins = max(window_sec // 60, 1)
            return f"Demasiados intentos. Espera {mins} minuto(s) e inténtalo de nuevo."
        bucket.append(now)
    return None


def record_attempt(scope: str, key: str) -> None:
    with _lock:
        _buckets[scope][key].append(time.time())


def clear_attempts(scope: str, key: str) -> None:
    with _lock:
        _buckets[scope].pop(key, None)


def reset_all() -> None:
    """Solo para tests."""
    with _lock:
        _buckets.clear()
