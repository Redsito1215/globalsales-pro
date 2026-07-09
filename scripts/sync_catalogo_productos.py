"""Regenera dim_categoria + dim_producto (120 SKUs) y borra colecciones espejo."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

from paquetes.tablero import catalogo, catalogo_modelo

if __name__ == "__main__":
    v = catalogo_modelo.verify_category_totals("Snacks")
    print("Verificación Snacks:", v)
    r = catalogo.sync_products_to_mongo()
    print("Sincronizado:", r)
