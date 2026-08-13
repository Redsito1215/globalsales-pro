#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga imágenes de producto (Wikipedia) y actualiza dim_producto + tienda.

Uso:
  python scripts/seed_product_images.py
  python scripts/seed_product_images.py --dry-run
  python scripts/seed_product_images.py --force   # reemplaza imágenes existentes

Con Docker:
  docker compose exec api python scripts/seed_product_images.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))


def _load_module(name: str, rel_path: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


imgs = _load_module("catalogo_imagenes", "paquetes/tablero/catalogo_imagenes.py")
nombres = _load_module("catalogo_nombres", "paquetes/tablero/catalogo_nombres.py")

USER_AGENT = "GlobTradeCatalog/1.0 (educational demo; contact: admin@globtrade.local)"
IMG_SIZE = imgs.IMG_SIZE


def _wiki_thumbnail(query: str) -> str | None:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 0,
            "gsrlimit": 1,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": IMG_SIZE,
            "format": "json",
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if thumb:
            return str(thumb)
    return None


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(req, timeout=30) as resp:
        raw = resp.read()
    if len(raw) < 500:
        raise ValueError("imagen demasiado pequeña")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)


def _should_skip(product_id: int, force: bool) -> bool:
    if force:
        return False
    return imgs.local_image_url(product_id) is not None


def seed_images(*, dry_run: bool = False, force: bool = False, pause: float = 0.25) -> dict[str, int]:
    from paquetes.shop import services as shop_services
    from shared.mongo import get_db

    db = get_db() if not dry_run else None
    ok = fail = skip = 0
    imgs.STATIC_DIR.mkdir(parents=True, exist_ok=True)

    for prod in nombres.OFFICIAL_PRODUCTS:
        pid = int(prod["product_id"])
        name = str(prod["name"])
        if _should_skip(pid, force):
            skip += 1
            continue

        query = imgs.wiki_search_term(pid, name)
        dest = imgs.image_abs_path(pid, "jpg")
        rel = imgs.image_rel_path(pid, "jpg")

        try:
            thumb = imgs.direct_image_url(pid) if hasattr(imgs, "direct_image_url") else None
            if not thumb:
                thumb = getattr(imgs, "DIRECT_URL", {}).get(pid)
            if not thumb:
                thumb = _wiki_thumbnail(query)
            if not thumb and query != name:
                thumb = _wiki_thumbnail(name)
            if not thumb:
                print(f"  ! {pid:3d} {name} — sin imagen en Wikipedia")
                fail += 1
                continue
            if dry_run:
                print(f"  ~ {pid:3d} {name} <- {thumb[:72]}…")
                ok += 1
                continue
            _download(thumb, dest)
            if db is not None:
                db["dim_producto"].update_one(
                {"product_id": pid},
                {"$set": {"image_url": rel, "image_source": "catalog_seed"}},
                    upsert=False,
                )
            print(f"  + {pid:3d} {name}")
            ok += 1
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"  ! {pid:3d} {name} — {exc}")
            fail += 1
        time.sleep(pause)

    if not dry_run and ok:
        shop_services.sync_from_masters()
    return {"ok": ok, "fail": fail, "skip": skip}


def main() -> int:
    parser = argparse.ArgumentParser(description="Imágenes de catálogo GLOBTRADE (120 productos)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué se descargaría")
    parser.add_argument("--force", action="store_true", help="Reemplaza imágenes locales existentes")
    args = parser.parse_args()

    print("GLOBTRADE — seed imágenes de producto")
    print(f"Destino: {imgs.STATIC_DIR}")
    try:
        stats = seed_images(dry_run=args.dry_run, force=args.force)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"\nListo: {stats['ok']} ok, {stats['fail']} fallos, {stats['skip']} omitidos.")
    if not args.dry_run and stats["ok"]:
        print("Tienda sincronizada (product_media actualizado).")
    return 0 if stats["fail"] == 0 or stats["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
