"""Registro de páginas y permisos configurables por rol."""
from __future__ import annotations

from typing import Any

# Páginas SPA (data-page)
PAGE_CATALOG: dict[str, dict[str, str]] = {
    "dashboard": {"label": "Tablero estratégico", "section": "q2"},
    "tienda": {"label": "Tienda", "section": "ops"},
    "mis-pedidos": {"label": "Mis pedidos", "section": "ops"},
    "ventas": {"label": "Pedidos y ventas", "section": "ops"},
    "compras": {"label": "Compras e inventario", "section": "ops"},
    "notificaciones": {"label": "Notificaciones", "section": "ops"},
    "soporte": {"label": "Soporte", "section": "ops"},
    "decisiones": {"label": "Decisiones", "section": "q2"},
    "reportes-compuestos": {"label": "Informes compuestos", "section": "q2"},
    "orders": {"label": "Explorar ventas", "section": "gestion"},
    "trends": {"label": "Tendencia de ventas", "section": "q2"},
    "regions": {"label": "Ventas por región", "section": "q2"},
    "products": {"label": "Ventas por categoría", "section": "q2"},
    "catalogo": {"label": "Catálogo analítico", "section": "gestion"},
    "reportes": {"label": "Informes operativos", "section": "gestion"},
    "export": {"label": "Descargar datos", "section": "gestion"},
    "company": {"label": "Empresa", "section": "admin"},
    "gestion": {"label": "Maestros tácticos", "section": "gestion"},
    "schema": {"label": "Modelo de datos", "section": "admin"},
    "load": {"label": "Carga de datos", "section": "admin"},
    "audit": {"label": "Auditoría", "section": "admin"},
    "roles-admin": {"label": "Roles y usuarios", "section": "admin"},
}

SECTION_LABELS: dict[str, str] = {
    "ops": "Operativo",
    "q2": "Estratégico",
    "gestion": "Táctico",
    "admin": "Administración",
}

PERMISSION_CATALOG: dict[str, str] = {
    "shop.checkout": "Solicitar compra en vitrina",
    "shop.view": "Ver catálogo tienda",
    "orders.read": "Explorar ventas históricas",
    "analysis.export": "Exportar PDF",
    "decisiones.view": "Panel de decisiones de negocio",
    "ventas.manage": "Gestionar solicitudes comerciales",
    "ventas.convert_bypass": "Convertir venta sin aprobación previa",
    "soporte.inbox": "Bandeja de soporte / hilos de clientes",
    "masters.read": "Consultar maestros",
    "masters.write": "Editar maestros y sync de catálogo",
    "compras.manage": "Proveedores, inventario y órdenes de compra",
    "reportes.view": "Ver reportes simples operativos (Tarea 11)",
    "elt.run": "Ejecutar carga ELT / build modelo",
    "audit.read": "Ver auditoría",
    "users.manage": "Gestionar usuarios y roles",
    "company.manage": "Editar datos de la empresa y logo en facturas",
}

DEFAULT_ROLES: list[dict[str, Any]] = [
    {
        "slug": "cliente",
        "label": "Cliente B2B",
        "system": True,
        "assignable": True,
        "pages": ["tienda", "company", "mis-pedidos", "soporte", "notificaciones"],
        "permissions": ["shop.view", "shop.checkout"],
    },
    {
        "slug": "vendedor",
        "label": "Vendedor comercial",
        "system": True,
        "assignable": True,
        "pages": [
            "tienda",
            "company",
            "ventas",
            "compras",
            "reportes",
            "reportes-compuestos",
            "orders",
            "decisiones",
            "mis-pedidos",
            "soporte",
            "notificaciones",
        ],
        "permissions": [
            "shop.view",
            "shop.checkout",
            "ventas.manage",
            "compras.manage",
            "reportes.view",
            "orders.read",
            "soporte.inbox",
            "decisiones.view",
        ],
    },
    {
        "slug": "analista",
        "label": "Analista",
        "system": True,
        "assignable": True,
        "pages": [
            "dashboard",
            "catalogo",
            "company",
            "trends",
            "regions",
            "products",
            "export",
            "decisiones",
            "reportes-compuestos",
            "tienda",
            "orders",
            "ventas",
            "reportes",
            "soporte",
            "notificaciones",
        ],
        "permissions": [
            "shop.view",
            "orders.read",
            "analysis.export",
            "decisiones.view",
            "reportes.view",
        ],
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
