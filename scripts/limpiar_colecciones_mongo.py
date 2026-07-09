"""Elimina solo colecciones duplicadas del catálogo (products, product_categories)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from shared.collections_q1 import DUPLICATE_CATALOG_COLLECTIONS, drop_duplicate_catalog_collections
from shared.mongo import get_db

if __name__ == "__main__":
    db = get_db()
    print("Antes:", sorted(db.list_collection_names()))
    dropped = drop_duplicate_catalog_collections(db)
    if dropped:
        for name in dropped:
            print(f"  eliminada: {name}")
    else:
        print("  (no había duplicados de catálogo)")
    print("Después:", sorted(db.list_collection_names()))
    print("Duplicados que no deben existir:", list(DUPLICATE_CATALOG_COLLECTIONS))
