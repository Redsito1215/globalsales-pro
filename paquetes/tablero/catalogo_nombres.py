"""Catálogo oficial: product_id, category_id y nombre (120 productos)."""
from __future__ import annotations

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

OFFICIAL_PRODUCTS: list[dict] = [
    # Category 1 — Baby Food
    {"product_id": 71, "category_id": 1, "name": "Apple Puree"},
    {"product_id": 72, "category_id": 1, "name": "Banana Mash"},
    {"product_id": 73, "category_id": 1, "name": "Rice Cereal"},
    {"product_id": 74, "category_id": 1, "name": "Sweet Potato Puree"},
    {"product_id": 75, "category_id": 1, "name": "Oatmeal Baby Porridge"},
    {"product_id": 76, "category_id": 1, "name": "Carrot Puree"},
    {"product_id": 77, "category_id": 1, "name": "Baby Formula Milk"},
    {"product_id": 78, "category_id": 1, "name": "Pear & Mango Blend"},
    {"product_id": 79, "category_id": 1, "name": "Chicken & Veggie Puree"},
    {"product_id": 80, "category_id": 1, "name": "Baby Yogurt"},
    # Category 2 — Beverages
    {"product_id": 81, "category_id": 2, "name": "Orange Juice"},
    {"product_id": 82, "category_id": 2, "name": "Sparkling Water"},
    {"product_id": 83, "category_id": 2, "name": "Green Tea"},
    {"product_id": 84, "category_id": 2, "name": "Energy Drink"},
    {"product_id": 85, "category_id": 2, "name": "Whole Milk"},
    {"product_id": 86, "category_id": 2, "name": "Black Coffee"},
    {"product_id": 87, "category_id": 2, "name": "Coconut Water"},
    {"product_id": 88, "category_id": 2, "name": "Sports Drink"},
    {"product_id": 89, "category_id": 2, "name": "Lemonade"},
    {"product_id": 90, "category_id": 2, "name": "Iced Tea"},
    # Category 3 — Cereal
    {"product_id": 91, "category_id": 3, "name": "Corn Flakes"},
    {"product_id": 92, "category_id": 3, "name": "Rolled Oats"},
    {"product_id": 93, "category_id": 3, "name": "Granola Mix"},
    {"product_id": 94, "category_id": 3, "name": "Honey Puffs"},
    {"product_id": 95, "category_id": 3, "name": "Wheat Bran"},
    {"product_id": 96, "category_id": 3, "name": "Muesli"},
    {"product_id": 97, "category_id": 3, "name": "Chocolate Pops"},
    {"product_id": 98, "category_id": 3, "name": "Brown Rice Flakes"},
    {"product_id": 99, "category_id": 3, "name": "Quinoa Puffs"},
    {"product_id": 100, "category_id": 3, "name": "Multi-Grain Loops"},
    # Category 4 — Clothes
    {"product_id": 101, "category_id": 4, "name": "Men's Cotton T-Shirt"},
    {"product_id": 102, "category_id": 4, "name": "Women's Jeans"},
    {"product_id": 103, "category_id": 4, "name": "Kids' Hoodie"},
    {"product_id": 104, "category_id": 4, "name": "Sports Shorts"},
    {"product_id": 105, "category_id": 4, "name": "Winter Jacket"},
    {"product_id": 106, "category_id": 4, "name": "Polo Shirt"},
    {"product_id": 107, "category_id": 4, "name": "Dress Pants"},
    {"product_id": 108, "category_id": 4, "name": "Casual Sneakers"},
    {"product_id": 109, "category_id": 4, "name": "Rain Coat"},
    {"product_id": 110, "category_id": 4, "name": "Summer Dress"},
    # Category 5 — Cosmetics
    {"product_id": 111, "category_id": 5, "name": "Foundation Cream"},
    {"product_id": 112, "category_id": 5, "name": "Mascara"},
    {"product_id": 113, "category_id": 5, "name": "Lipstick"},
    {"product_id": 114, "category_id": 5, "name": "Eyeshadow Palette"},
    {"product_id": 115, "category_id": 5, "name": "Blush Powder"},
    {"product_id": 116, "category_id": 5, "name": "Concealer"},
    {"product_id": 117, "category_id": 5, "name": "Setting Spray"},
    {"product_id": 118, "category_id": 5, "name": "Highlighter"},
    {"product_id": 119, "category_id": 5, "name": "Eyeliner Pencil"},
    {"product_id": 120, "category_id": 5, "name": "Nail Polish"},
    # Category 6 — Fruits
    {"product_id": 1, "category_id": 6, "name": "Fresh Mangoes"},
    {"product_id": 2, "category_id": 6, "name": "Red Apples"},
    {"product_id": 3, "category_id": 6, "name": "Bananas"},
    {"product_id": 4, "category_id": 6, "name": "Pineapples"},
    {"product_id": 5, "category_id": 6, "name": "Watermelons"},
    {"product_id": 6, "category_id": 6, "name": "Grapes"},
    {"product_id": 7, "category_id": 6, "name": "Oranges"},
    {"product_id": 8, "category_id": 6, "name": "Strawberries"},
    {"product_id": 9, "category_id": 6, "name": "Peaches"},
    {"product_id": 10, "category_id": 6, "name": "Papayas"},
    # Category 7 — Household
    {"product_id": 11, "category_id": 7, "name": "Laundry Detergent"},
    {"product_id": 12, "category_id": 7, "name": "Dish Soap"},
    {"product_id": 13, "category_id": 7, "name": "Mop Set"},
    {"product_id": 14, "category_id": 7, "name": "Broom & Dustpan"},
    {"product_id": 15, "category_id": 7, "name": "Trash Bags"},
    {"product_id": 16, "category_id": 7, "name": "Fabric Softener"},
    {"product_id": 17, "category_id": 7, "name": "Sponges Pack"},
    {"product_id": 18, "category_id": 7, "name": "Air Freshener"},
    {"product_id": 19, "category_id": 7, "name": "Rubber Gloves"},
    {"product_id": 20, "category_id": 7, "name": "Cleaning Spray"},
    # Category 8 — Meat
    {"product_id": 21, "category_id": 8, "name": "Chicken Breast"},
    {"product_id": 22, "category_id": 8, "name": "Ground Beef"},
    {"product_id": 23, "category_id": 8, "name": "Pork Ribs"},
    {"product_id": 24, "category_id": 8, "name": "Lamb Chops"},
    {"product_id": 25, "category_id": 8, "name": "Turkey Breast"},
    {"product_id": 26, "category_id": 8, "name": "Beef Tenderloin"},
    {"product_id": 27, "category_id": 8, "name": "Pork Sausages"},
    {"product_id": 28, "category_id": 8, "name": "Salmon Fillet"},
    {"product_id": 29, "category_id": 8, "name": "Tuna Steaks"},
    {"product_id": 30, "category_id": 8, "name": "Shrimp"},
    # Category 9 — Office Supplies
    {"product_id": 31, "category_id": 9, "name": "Ballpoint Pens Pack"},
    {"product_id": 32, "category_id": 9, "name": "Stapler"},
    {"product_id": 33, "category_id": 9, "name": "Sticky Notes"},
    {"product_id": 34, "category_id": 9, "name": "Printer Paper A4"},
    {"product_id": 35, "category_id": 9, "name": "Binder Clips"},
    {"product_id": 36, "category_id": 9, "name": "Whiteboard Markers"},
    {"product_id": 37, "category_id": 9, "name": "File Folders"},
    {"product_id": 38, "category_id": 9, "name": "Scissors"},
    {"product_id": 39, "category_id": 9, "name": "Tape Dispenser"},
    {"product_id": 40, "category_id": 9, "name": "Notebook Spiral"},
    # Category 10 — Personal Care
    {"product_id": 41, "category_id": 10, "name": "Shampoo"},
    {"product_id": 42, "category_id": 10, "name": "Conditioner"},
    {"product_id": 43, "category_id": 10, "name": "Body Lotion"},
    {"product_id": 44, "category_id": 10, "name": "Toothpaste"},
    {"product_id": 45, "category_id": 10, "name": "Deodorant"},
    {"product_id": 46, "category_id": 10, "name": "Face Wash"},
    {"product_id": 47, "category_id": 10, "name": "Shower Gel"},
    {"product_id": 48, "category_id": 10, "name": "Razors Pack"},
    {"product_id": 49, "category_id": 10, "name": "Cotton Swabs"},
    {"product_id": 50, "category_id": 10, "name": "Sunscreen SPF50"},
    # Category 11 — Snacks
    {"product_id": 51, "category_id": 11, "name": "Potato Chips"},
    {"product_id": 52, "category_id": 11, "name": "Popcorn"},
    {"product_id": 53, "category_id": 11, "name": "Granola Bars"},
    {"product_id": 54, "category_id": 11, "name": "Pretzels"},
    {"product_id": 55, "category_id": 11, "name": "Cheese Crackers"},
    {"product_id": 56, "category_id": 11, "name": "Trail Mix"},
    {"product_id": 57, "category_id": 11, "name": "Rice Cakes"},
    {"product_id": 58, "category_id": 11, "name": "Peanut Butter Cups"},
    {"product_id": 59, "category_id": 11, "name": "Beef Jerky"},
    {"product_id": 60, "category_id": 11, "name": "Dried Mango Strips"},
    # Category 12 — Vegetables
    {"product_id": 61, "category_id": 12, "name": "Broccoli"},
    {"product_id": 62, "category_id": 12, "name": "Carrots"},
    {"product_id": 63, "category_id": 12, "name": "Spinach"},
    {"product_id": 64, "category_id": 12, "name": "Tomatoes"},
    {"product_id": 65, "category_id": 12, "name": "Bell Peppers"},
    {"product_id": 66, "category_id": 12, "name": "Zucchini"},
    {"product_id": 67, "category_id": 12, "name": "Onions"},
    {"product_id": 68, "category_id": 12, "name": "Garlic Bulbs"},
    {"product_id": 69, "category_id": 12, "name": "Cucumbers"},
    {"product_id": 70, "category_id": 12, "name": "Lettuce"},
]

_BY_CATEGORY: dict[int, list[dict]] = {}


def _index() -> dict[int, list[dict]]:
    global _BY_CATEGORY
    if not _BY_CATEGORY:
        for p in OFFICIAL_PRODUCTS:
            _BY_CATEGORY.setdefault(int(p["category_id"]), []).append(p)
        for cid in _BY_CATEGORY:
            _BY_CATEGORY[cid].sort(key=lambda x: int(x["product_id"]))
    return _BY_CATEGORY


def products_for_category(category_id: int) -> list[dict]:
    return list(_index().get(int(category_id), []))


def category_name(category_id: int) -> str:
    return CATEGORY_BY_ID[int(category_id)]


def product_display_name(category: str, line: int) -> str:
    """Compatibilidad: resuelve por categoría + línea 1..10."""
    cid = next((k for k, v in CATEGORY_BY_ID.items() if v == category), None)
    if cid is None:
        return f"{category} - Ref.{line}"
    items = products_for_category(cid)
    if 1 <= line <= len(items):
        return items[line - 1]["name"]
    return f"{category} - Ref.{line}"
