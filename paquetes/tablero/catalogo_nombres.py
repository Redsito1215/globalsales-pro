"""Catálogo oficial: product_id, category_id y nombre (120 productos)."""
from __future__ import annotations

# Claves en inglés para ETL / sales_records (item_type). No cambiar.
CATEGORY_BY_ID: dict[int, str] = {
    1: "Baby Food",
    2: "Beverages",
    3: "Cereal",
    4: "Clothes",
    5: "Cosmetics",
    6: "Fruits",
    7: "Household",
    8: "Meat",
    9: "Office Supplies",
    10: "Personal Care",
    11: "Snacks",
    12: "Vegetables",
}

# Etiquetas en español para vitrina y maestros visibles al usuario.
CATEGORY_LABEL_ES: dict[int, str] = {
    1: "Alimentos para bebés",
    2: "Bebidas",
    3: "Cereales",
    4: "Ropa",
    5: "Cosméticos",
    6: "Frutas",
    7: "Hogar",
    8: "Carnes",
    9: "Oficina",
    10: "Cuidado personal",
    11: "Snacks",
    12: "Verduras",
}

OFFICIAL_PRODUCTS: list[dict] = [
    # Category 1 — Baby Food
    {"product_id": 71, "category_id": 1, "name": "Puré de manzana"},
    {"product_id": 72, "category_id": 1, "name": "Puré de plátano"},
    {"product_id": 73, "category_id": 1, "name": "Cereal de arroz"},
    {"product_id": 74, "category_id": 1, "name": "Puré de camote"},
    {"product_id": 75, "category_id": 1, "name": "Papilla de avena"},
    {"product_id": 76, "category_id": 1, "name": "Puré de zanahoria"},
    {"product_id": 77, "category_id": 1, "name": "Leche de fórmula"},
    {"product_id": 78, "category_id": 1, "name": "Mezcla de pera y mango"},
    {"product_id": 79, "category_id": 1, "name": "Puré de pollo y verduras"},
    {"product_id": 80, "category_id": 1, "name": "Yogur para bebé"},
    # Category 2 — Beverages
    {"product_id": 81, "category_id": 2, "name": "Jugo de naranja"},
    {"product_id": 82, "category_id": 2, "name": "Agua con gas"},
    {"product_id": 83, "category_id": 2, "name": "Té verde"},
    {"product_id": 84, "category_id": 2, "name": "Bebida energética"},
    {"product_id": 85, "category_id": 2, "name": "Leche entera"},
    {"product_id": 86, "category_id": 2, "name": "Café negro"},
    {"product_id": 87, "category_id": 2, "name": "Agua de coco"},
    {"product_id": 88, "category_id": 2, "name": "Bebida deportiva"},
    {"product_id": 89, "category_id": 2, "name": "Limonada"},
    {"product_id": 90, "category_id": 2, "name": "Té frío"},
    # Category 3 — Cereal
    {"product_id": 91, "category_id": 3, "name": "Hojuelas de maíz"},
    {"product_id": 92, "category_id": 3, "name": "Avena en hojuelas"},
    {"product_id": 93, "category_id": 3, "name": "Mezcla de granola"},
    {"product_id": 94, "category_id": 3, "name": "Cereal con miel"},
    {"product_id": 95, "category_id": 3, "name": "Salvado de trigo"},
    {"product_id": 96, "category_id": 3, "name": "Muesli"},
    {"product_id": 97, "category_id": 3, "name": "Cereal de chocolate"},
    {"product_id": 98, "category_id": 3, "name": "Hojuelas de arroz integral"},
    {"product_id": 99, "category_id": 3, "name": "Cereal de quinoa"},
    {"product_id": 100, "category_id": 3, "name": "Cereales multigrano"},
    # Category 4 — Clothes
    {"product_id": 101, "category_id": 4, "name": "Camiseta de algodón hombre"},
    {"product_id": 102, "category_id": 4, "name": "Jeans mujer"},
    {"product_id": 103, "category_id": 4, "name": "Sudadera infantil"},
    {"product_id": 104, "category_id": 4, "name": "Shorts deportivos"},
    {"product_id": 105, "category_id": 4, "name": "Chaqueta de invierno"},
    {"product_id": 106, "category_id": 4, "name": "Camisa polo"},
    {"product_id": 107, "category_id": 4, "name": "Pantalón de vestir"},
    {"product_id": 108, "category_id": 4, "name": "Zapatillas casuales"},
    {"product_id": 109, "category_id": 4, "name": "Impermeable"},
    {"product_id": 110, "category_id": 4, "name": "Vestido de verano"},
    # Category 5 — Cosmetics
    {"product_id": 111, "category_id": 5, "name": "Base de maquillaje"},
    {"product_id": 112, "category_id": 5, "name": "Máscara de pestañas"},
    {"product_id": 113, "category_id": 5, "name": "Labial"},
    {"product_id": 114, "category_id": 5, "name": "Paleta de sombras"},
    {"product_id": 115, "category_id": 5, "name": "Rubor en polvo"},
    {"product_id": 116, "category_id": 5, "name": "Corrector"},
    {"product_id": 117, "category_id": 5, "name": "Fijador de maquillaje"},
    {"product_id": 118, "category_id": 5, "name": "Iluminador"},
    {"product_id": 119, "category_id": 5, "name": "Lápiz delineador"},
    {"product_id": 120, "category_id": 5, "name": "Esmalte de uñas"},
    # Category 6 — Fruits
    {"product_id": 1, "category_id": 6, "name": "Mangos frescos"},
    {"product_id": 2, "category_id": 6, "name": "Manzanas rojas"},
    {"product_id": 3, "category_id": 6, "name": "Plátanos"},
    {"product_id": 4, "category_id": 6, "name": "Piñas"},
    {"product_id": 5, "category_id": 6, "name": "Sandías"},
    {"product_id": 6, "category_id": 6, "name": "Uvas"},
    {"product_id": 7, "category_id": 6, "name": "Naranjas"},
    {"product_id": 8, "category_id": 6, "name": "Fresas"},
    {"product_id": 9, "category_id": 6, "name": "Duraznos"},
    {"product_id": 10, "category_id": 6, "name": "Papayas"},
    # Category 7 — Household
    {"product_id": 11, "category_id": 7, "name": "Detergente para ropa"},
    {"product_id": 12, "category_id": 7, "name": "Jabón para trastes"},
    {"product_id": 13, "category_id": 7, "name": "Juego de trapeador"},
    {"product_id": 14, "category_id": 7, "name": "Escoba y recogedor"},
    {"product_id": 15, "category_id": 7, "name": "Bolsas de basura"},
    {"product_id": 16, "category_id": 7, "name": "Suavizante de telas"},
    {"product_id": 17, "category_id": 7, "name": "Paquete de esponjas"},
    {"product_id": 18, "category_id": 7, "name": "Ambientador"},
    {"product_id": 19, "category_id": 7, "name": "Guantes de hule"},
    {"product_id": 20, "category_id": 7, "name": "Limpiador multiusos"},
    # Category 8 — Meat
    {"product_id": 21, "category_id": 8, "name": "Pechuga de pollo"},
    {"product_id": 22, "category_id": 8, "name": "Carne molida de res"},
    {"product_id": 23, "category_id": 8, "name": "Costillas de cerdo"},
    {"product_id": 24, "category_id": 8, "name": "Chuletas de cordero"},
    {"product_id": 25, "category_id": 8, "name": "Pechuga de pavo"},
    {"product_id": 26, "category_id": 8, "name": "Filete de res"},
    {"product_id": 27, "category_id": 8, "name": "Salchichas de cerdo"},
    {"product_id": 28, "category_id": 8, "name": "Filete de salmón"},
    {"product_id": 29, "category_id": 8, "name": "Medallones de atún"},
    {"product_id": 30, "category_id": 8, "name": "Camarones"},
    # Category 9 — Office Supplies
    {"product_id": 31, "category_id": 9, "name": "Paquete de bolígrafos"},
    {"product_id": 32, "category_id": 9, "name": "Engrapadora"},
    {"product_id": 33, "category_id": 9, "name": "Notas adhesivas"},
    {"product_id": 34, "category_id": 9, "name": "Papel bond A4"},
    {"product_id": 35, "category_id": 9, "name": "Clips para carpeta"},
    {"product_id": 36, "category_id": 9, "name": "Marcadores para pizarra"},
    {"product_id": 37, "category_id": 9, "name": "Carpetas de archivo"},
    {"product_id": 38, "category_id": 9, "name": "Tijeras"},
    {"product_id": 39, "category_id": 9, "name": "Dispensador de cinta"},
    {"product_id": 40, "category_id": 9, "name": "Cuaderno espiral"},
    # Category 10 — Personal Care
    {"product_id": 41, "category_id": 10, "name": "Champú"},
    {"product_id": 42, "category_id": 10, "name": "Acondicionador"},
    {"product_id": 43, "category_id": 10, "name": "Loción corporal"},
    {"product_id": 44, "category_id": 10, "name": "Pasta dental"},
    {"product_id": 45, "category_id": 10, "name": "Desodorante"},
    {"product_id": 46, "category_id": 10, "name": "Limpiador facial"},
    {"product_id": 47, "category_id": 10, "name": "Gel de baño"},
    {"product_id": 48, "category_id": 10, "name": "Paquete de rastrillos"},
    {"product_id": 49, "category_id": 10, "name": "Hisopos de algodón"},
    {"product_id": 50, "category_id": 10, "name": "Protector solar FPS 50"},
    # Category 11 — Snacks
    {"product_id": 51, "category_id": 11, "name": "Papas fritas"},
    {"product_id": 52, "category_id": 11, "name": "Palomitas"},
    {"product_id": 53, "category_id": 11, "name": "Barras de granola"},
    {"product_id": 54, "category_id": 11, "name": "Pretzels"},
    {"product_id": 55, "category_id": 11, "name": "Galletas con queso"},
    {"product_id": 56, "category_id": 11, "name": "Mezcla de frutos secos"},
    {"product_id": 57, "category_id": 11, "name": "Galletas de arroz"},
    {"product_id": 58, "category_id": 11, "name": "Chocolates con crema de cacahuate"},
    {"product_id": 59, "category_id": 11, "name": "Carne seca"},
    {"product_id": 60, "category_id": 11, "name": "Tiras de mango deshidratado"},
    # Category 12 — Vegetables
    {"product_id": 61, "category_id": 12, "name": "Brócoli"},
    {"product_id": 62, "category_id": 12, "name": "Zanahorias"},
    {"product_id": 63, "category_id": 12, "name": "Espinaca"},
    {"product_id": 64, "category_id": 12, "name": "Tomates"},
    {"product_id": 65, "category_id": 12, "name": "Pimientos morrones"},
    {"product_id": 66, "category_id": 12, "name": "Calabacín"},
    {"product_id": 67, "category_id": 12, "name": "Cebollas"},
    {"product_id": 68, "category_id": 12, "name": "Bulbos de ajo"},
    {"product_id": 69, "category_id": 12, "name": "Pepinos"},
    {"product_id": 70, "category_id": 12, "name": "Lechuga"},
]

_BY_CATEGORY: dict[int, list[dict]] = {}
_BY_PRODUCT_ID: dict[int, dict] = {}


def _index() -> dict[int, list[dict]]:
    global _BY_CATEGORY
    if not _BY_CATEGORY:
        for p in OFFICIAL_PRODUCTS:
            _BY_CATEGORY.setdefault(int(p["category_id"]), []).append(p)
        for cid in _BY_CATEGORY:
            _BY_CATEGORY[cid].sort(key=lambda x: int(x["product_id"]))
    return _BY_CATEGORY


def _product_index() -> dict[int, dict]:
    global _BY_PRODUCT_ID
    if not _BY_PRODUCT_ID:
        for p in OFFICIAL_PRODUCTS:
            _BY_PRODUCT_ID[int(p["product_id"])] = p
    return _BY_PRODUCT_ID


def products_for_category(category_id: int) -> list[dict]:
    return list(_index().get(int(category_id), []))


def category_name(category_id: int) -> str:
    """Clave inglesa (item_type) para ETL y tablero."""
    return CATEGORY_BY_ID[int(category_id)]


def category_display_name(category_id: int) -> str:
    """Etiqueta en español para vitrina y listados."""
    cid = int(category_id)
    return CATEGORY_LABEL_ES.get(cid, CATEGORY_BY_ID.get(cid, ""))


_CATEGORY_EN_TO_ES: dict[str, str] = {
    en: CATEGORY_LABEL_ES[cid] for cid, en in CATEGORY_BY_ID.items()
}


def category_label_from_name(
    name: str | None,
    *,
    category_id: int | None = None,
) -> str:
    """Traduce clave inglesa (dim_categoria / item_type) a etiqueta ES para la UI."""
    if category_id is not None:
        return category_display_name(int(category_id))
    label = (name or "").strip()
    if not label or label in {"—", "Sin categoría"}:
        return label or "—"
    mapped = _CATEGORY_EN_TO_ES.get(label)
    if mapped:
        return mapped
    for cid, es in CATEGORY_LABEL_ES.items():
        if label == es:
            return es
    cid = next((k for k, en in CATEGORY_BY_ID.items() if en == label), None)
    if cid is not None:
        return category_display_name(cid)
    return label


def product_display_name_by_id(product_id: int, fallback: str = "") -> str:
    row = _product_index().get(int(product_id))
    if row:
        return str(row["name"])
    return fallback


def product_display_name(category: str, line: int) -> str:
    """Compatibilidad: resuelve por categoría + línea 1..10."""
    cid = next((k for k, v in CATEGORY_BY_ID.items() if v == category), None)
    if cid is None:
        return f"{category} - Ref.{line}"
    items = products_for_category(cid)
    if 1 <= line <= len(items):
        return items[line - 1]["name"]
    return f"{category_display_name(cid)} - Ref.{line}"
