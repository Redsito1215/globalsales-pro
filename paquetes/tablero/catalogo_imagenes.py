"""Imágenes por defecto del catálogo (120 productos)."""
from __future__ import annotations

from pathlib import Path

from config.settings import ROOT

IMG_SIZE = 400
STATIC_REL = "/static/img/products"
STATIC_DIR = ROOT / "frontend" / "static" / "img" / "products"

# Término de búsqueda Wikipedia cuando el nombre del producto no devuelve buen resultado.
WIKI_SEARCH: dict[int, str] = {
    71: "apple sauce baby food",
    72: "mashed banana",
    73: "baby rice cereal",
    74: "sweet potato puree",
    75: "baby oatmeal porridge",
    76: "carrot baby food puree",
    77: "infant formula milk powder",
    78: "pear mango baby food",
    79: "chicken vegetable baby food",
    80: "baby yogurt",
    84: "energy drink can",
    88: "sports drink bottle",
    94: "honey puffs cereal",
    97: "chocolate cereal pops",
    100: "multigrain cereal loops",
    101: "cotton t-shirt",
    102: "blue jeans",
    103: "children hoodie",
    104: "athletic shorts",
    105: "winter jacket",
    106: "polo shirt",
    107: "dress pants",
    108: "sneakers shoes",
    109: "raincoat",
    110: "summer dress",
    111: "liquid foundation makeup",
    112: "mascara cosmetics",
    113: "lipstick",
    114: "eyeshadow palette",
    115: "blush powder makeup",
    116: "concealer makeup",
    117: "makeup setting spray",
    118: "highlighter makeup",
    119: "eyeliner pencil",
    120: "nail polish bottle",
    13: "mop cleaning",
    14: "broom dustpan",
    17: "kitchen sponges",
    31: "ballpoint pens",
    35: "binder clips office",
    36: "whiteboard markers",
    39: "tape dispenser office",
    40: "spiral notebook",
    48: "disposable razors",
    49: "cotton swabs",
    53: "granola bars",
    55: "cheese crackers snack",
    57: "rice cakes snack",
    58: "peanut butter cups candy",
    60: "dried mango strips",
    2: "red apple fruit",
    9: "peach fruit",
    16: "fabric softener bottle",
    24: "lamb chops meat",
    42: "hair conditioner bottle",
    45: "deodorant antiperspirant",
    46: "facial cleanser face wash",
    99: "quinoa cereal puffs",
}

# Respaldo directo (Wikimedia Commons) si Wikipedia no devuelve miniatura.
def _commons(file: str, width: int = 330) -> str:
    from urllib.parse import quote

    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(file)}?width={width}"


DIRECT_URL: dict[int, str] = {
    2: _commons("Red_Apple.jpg"),
    9: _commons("Peach_fruit.jpg"),
    16: _commons("Downy.jpg"),
    24: _commons("Lamb_meat.jpg"),
    42: _commons("Shampoo.jpg"),
    45: _commons("Deodorant.jpg"),
    46: _commons("Soap.jpg"),
    80: _commons("Yogurt.jpg"),
    94: _commons("Cereal.jpg"),
    99: _commons("Quinoa.jpg"),
    104: _commons("Boardshorts.jpg"),
    114: _commons("Eye_shadow_palette.jpg"),
    117: _commons("Spray_can.jpg"),
}


def image_rel_path(product_id: int, ext: str = "jpg") -> str:
    return f"{STATIC_REL}/{int(product_id)}.{ext.lstrip('.')}"


def image_abs_path(product_id: int, ext: str = "jpg") -> Path:
    return STATIC_DIR / f"{int(product_id)}.{ext.lstrip('.')}"


def local_image_url(product_id: int) -> str | None:
    """URL servida por Flask si el archivo local existe."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        if image_abs_path(product_id, ext).is_file():
            return image_rel_path(product_id, ext)
    return None


def wiki_search_term(product_id: int, name: str) -> str:
    return WIKI_SEARCH.get(int(product_id), name)


def direct_image_url(product_id: int) -> str | None:
    return DIRECT_URL.get(int(product_id))


def resolve_image_url(product_id: int, name: str, preserved: str | None = None) -> str | None:
    """Prioridad: upload manual > archivo local del catálogo."""
    if preserved:
        return preserved
    return local_image_url(product_id)
