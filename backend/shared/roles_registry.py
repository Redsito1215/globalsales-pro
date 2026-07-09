"""Registro de páginas y permisos configurables por rol."""
from __future__ import annotations

from typing import Any

# Páginas SPA (data-page)
PAGE_CATALOG: dict[str, dict[str, str]] = {
    "dashboard": {"label": "Tablero", "section": "q1"},
    "catalogo": {"label": "Catálogo DW", "section": "q1"},
    "trends": {"label": "Tendencias", "section": "q2"},
    "regions": {"label": "Regiones", "section": "q2"},
    "products": {"label": "Productos (análisis)", "section": "q2"},
    "export": {"label": "Exportar CSV", "section": "q2"},
    "tienda": {"label": "Vitrina B2B", "section": "tienda"},
    "mis-pedidos": {"label": "Mis pedidos", "section": "tienda"},
    "notificaciones": {"label": "Notificaciones", "section": "cuenta"},
    "soporte": {"label": "Soporte", "section": "cuenta"},
    "orders": {"label": "Explorar ventas", "section": "tienda"},
    "ventas": {"label": "Checkouts / Ventas", "section": "tienda"},
    "datos": {"label": "Maestros", "section": "q4"},
    "schema": {"label": "Modelo BD", "section": "q4"},
    "load": {"label": "Carga ELT", "section": "q4"},
    "audit": {"label": "Auditoría", "section": "q4"},
    "roles-admin": {"label": "Roles y usuarios", "section": "acceso"},
}

SECTION_LABELS: dict[str, str] = {
    "q1": "Q1 · Tablero",
    "q2": "Q2 · Análisis",
    "tienda": "Tienda online",
    "cuenta": "Mi cuenta",
    "q4": "Q4 · Datos",
    "acceso": "Administración",
}

PERMISSION_CATALOG: dict[str, str] = {
    "shop.checkout": "Checkout en vitrina",
    "shop.view": "Ver catálogo tienda",
    "orders.read": "Explorar ventas históricas",
    "analysis.export": "Exportar CSV",
    "ventas.manage": "Gestionar solicitudes comerciales",
    "ventas.convert_bypass": "Convertir venta sin aprobación previa",
    "masters.read": "Consultar maestros",
    "masters.write": "Editar maestros y sync Shopify",
    "elt.run": "Ejecutar carga ELT / build modelo",
    "audit.read": "Ver auditoría",
    "users.manage": "Gestionar usuarios y roles",
}

DEFAULT_ROLES: list[dict[str, Any]] = [
    {
        "slug": "cliente",
        "label": "Cliente B2B",
        "system": True,
        "assignable": True,
        "pages": ["tienda", "mis-pedidos", "soporte", "notificaciones"],
        "permissions": ["shop.view", "shop.checkout"],
    },
    {
        "slug": "vendedor",
        "label": "Vendedor comercial",
        "system": True,
        "assignable": True,
        "pages": ["tienda", "ventas", "mis-pedidos", "soporte", "notificaciones"],
        "permissions": ["shop.view", "shop.checkout", "ventas.manage"],
    },
    {
        "slug": "analista",
        "label": "Analista",
        "system": True,
        "assignable": True,
        "pages": ["dashboard", "trends", "regions", "products", "export", "tienda", "orders", "soporte", "notificaciones"],
        "permissions": ["shop.view", "shop.checkout", "orders.read", "analysis.export"],
    },
    {
        "slug": "administrador",
        "label": "Administrador",
        "system": True,
        "assignable": True,
        "pages": list(PAGE_CATALOG.keys()),
        "permissions": list(PERMISSION_CATALOG.keys()),
    },
]

VENDEDOR_ROLE = "vendedor"

# Visitante sin sesión: solo vitrina pública
PUBLIC_PAGES: list[str] = ["tienda"]

ADMIN_ROLE = "administrador"
DEFAULT_REGISTER_ROLE = "cliente"
