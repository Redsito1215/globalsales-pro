"""Lista y verifica manifiestos de respaldo sin restaurar ni modificar datos."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shared.backup_status import list_backup_manifests


def main() -> int:
    rows = list_backup_manifests(ROOT / "backups", limit=100)
    print(json.dumps({"count": len(rows), "backups": rows}, ensure_ascii=False, indent=2))
    return 0 if rows and all(row["verified"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
