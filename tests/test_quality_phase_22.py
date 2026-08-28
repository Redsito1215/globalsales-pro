"""Regresiones de calidad para catálogo, compras y experiencia de usuario."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))


def test_profile_rejects_invalid_phone_and_language():
    from auth.validators import validate_profile_update

    errors = validate_profile_update(
        name="Cliente Altavia",
        email="cliente@altavia.test",
        current_password="",
        new_password="",
        password_confirm="",
        email_changed=False,
        password_change=False,
        phone="solo letras",
        language="fr",
    )

    assert "phone" in errors
    assert "language" in errors


def test_profile_accepts_supported_locale_and_phone():
    from auth.validators import validate_profile_update

    errors = validate_profile_update(
        name="Cliente Altavia",
        email="cliente@altavia.test",
        current_password="",
        new_password="",
        password_confirm="",
        email_changed=False,
        password_change=False,
        phone="+593 99 123 4567",
        language="en",
    )

    assert errors == {}


def test_requested_ui_controls_remain_wired():
    index = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    orders = (ROOT / "frontend" / "static" / "js" / "mis-pedidos.js").read_text(encoding="utf-8")
    dialogs = (ROOT / "frontend" / "static" / "js" / "ops-ui.js").read_text(encoding="utf-8")
    products = (ROOT / "frontend" / "static" / "js" / "q4-datos.js").read_text(encoding="utf-8")

    assert index.count("data-password-toggle") >= 6
    assert "modal-card--request-detail" in index
    assert "Devoluciones" in orders
    assert "solicitar-devolucion" in orders
    assert "window.opsNotice" in dialogs
    assert "dim_producto: ['name', 'category_id', 'unit_price', 'unit_cost']" in products


def test_purchase_cost_validation_rejects_non_finite_values():
    source = (ROOT / "paquetes" / "compras" / "services.py").read_text(encoding="utf-8")

    assert source.count("not math.isfinite(cost) or cost <= 0") >= 2


def test_all_selects_use_searchable_overlay_with_context_filters():
    index = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    component = (ROOT / "frontend" / "static" / "js" / "smart-select.js").read_text(encoding="utf-8")
    purchases = (ROOT / "frontend" / "static" / "js" / "compras.js").read_text(encoding="utf-8")
    store = (ROOT / "frontend" / "static" / "js" / "tienda.js").read_text(encoding="utf-8")
    reports = (ROOT / "frontend" / "static" / "js" / "reportes.js").read_text(encoding="utf-8")
    masters = (ROOT / "frontend" / "static" / "js" / "q4-datos.js").read_text(encoding="utf-8")

    assert "/static/js/smart-select.js" in index
    assert "/static/css/smart-select.css" in index
    assert "MutationObserver" in component
    assert "Buscar por nombre, código o valor" in component
    assert "data-native-select" in component
    assert "data-filter-vendor" in purchases
    assert "data-filter-stock" in purchases
    assert "data-filter-category" in purchases
    assert "data-filter-country" in purchases
    assert "data-filter-region" in purchases
    assert "data-filter-region" in store
    assert "filterArea" in reports
    assert "data-filter-country" in masters


def test_store_category_selection_is_visible_and_invalidations_propagate():
    index = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    store = (ROOT / "frontend" / "static" / "js" / "tienda.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "static" / "css" / "storefront.css").read_text(encoding="utf-8")
    masters = (ROOT / "frontend" / "static" / "js" / "q4-datos.js").read_text(encoding="utf-8")
    shop_service = (ROOT / "paquetes" / "shop" / "services.py").read_text(encoding="utf-8")

    assert 'id="shop-active-category-name"' in index
    assert 'aria-current="${' in store
    assert "refreshStorefrontCatalog" in store
    assert "masterdata:changed" in store
    assert "masterdata:changed" in masters
    assert ".shop-collection-link.active::before" in styles
    assert "active_catalog_product_ids" in shop_service
