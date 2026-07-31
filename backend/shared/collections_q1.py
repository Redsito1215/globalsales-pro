"""Colecciones MongoDB — duplicados vs modelo dimensional."""
from __future__ import annotations

# Solo espejos legacy de categorías. `products` es catálogo OPERATIVO (vitrina);
# no dropear en build_model — se sincroniza con Maestros → Sync catálogo.
DUPLICATE_CATALOG_COLLECTIONS: tuple[str, ...] = (
    "product_categories",
)

# Espejos SQL opcionales (dim_* → nombre tipo schema.sql); Q1 no los lee en runtime
SQL_MIRROR_COLLECTIONS: tuple[str, ...] = (
    "regions",
    "countries",
    "sales_channels",
    "order_priorities",
    "clients",
)


def drop_duplicate_catalog_collections(db) -> list[str]:
    """Elimina solo products y product_categories."""
    dropped: list[str] = []
    for name in DUPLICATE_CATALOG_COLLECTIONS:
        if name in db.list_collection_names():
            db[name].drop()
            dropped.append(name)
    return dropped
