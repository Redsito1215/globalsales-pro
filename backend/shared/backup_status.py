"""Consulta segura de manifiestos de respaldo generados por scripts/backup_mongo.ps1."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def list_backup_manifests(root: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    base = root.resolve()
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        files = [p for p in path.parent.rglob("*") if p.is_file() and p.name != "manifest.json"]
        expected = int(data.get("file_count") or 0)
        rows.append({
            "backup_id": path.parent.name, "created_at": data.get("created_at"),
            "databases": data.get("databases") or [], "file_count": len(files),
            "verified": bool(files) and (expected == 0 or len(files) >= expected),
        })
    return rows
