# -*- coding: utf-8 -*-
"""Rate limiting en memoria por IP (demo / single-instance)."""
from __future__ import annotations

import time
from collections import defaultdict

_buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def check_rate_limit(
    scope: str,
    key: str,
    *,
    max_attempts: int,
    window_sec: int,
) -> str | None:
    now = time.time()
    bucket = _buckets[scope][key]
    bucket[:] = [t for t in bucket if now - t < window_sec]
    if len(bucket) >= max_attempts:
        mins = max(window_sec // 60, 1)
        return f"Demasiados intentos. Espera {mins} minuto(s) e inténtalo de nuevo."
    return None


def record_attempt(scope: str, key: str) -> None:
    _buckets[scope][key].append(time.time())


def clear_attempts(scope: str, key: str) -> None:
    _buckets[scope].pop(key, None)


def reset_all() -> None:
    """Solo para tests."""
    _buckets.clear()
