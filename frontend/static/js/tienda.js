/* Storefront B2B — colecciones, variantes, carrito, checkout */
let tiendaState = {
  collections: [],
  products: [],
  filtered: [],
  collectionId: null,
  cart: [],
  discountCode: '',
  discountAmount: 0,
  shippingCost: 0,
  shippingRegion: '',
  priceMax: null,
};

function shopMoney(n) {
  return '$' + Number(n || 0).toFixed(2);
}

function parsePositiveQty(raw, opts) {
  const o = opts || {};
  const text = String(raw ?? '').trim();
  if (!text || !/^\d+$/.test(text)) {
    if (o.notify !== false) notifyWarn(o.message || 'La cantidad debe ser un entero mayor a 0.');
    return null;
  }
  const n = parseInt(text, 10);
  if (!Number.isFinite(n) || n < 1) {
    if (o.notify !== false) notifyWarn(o.message || 'La cantidad debe ser un entero mayor a 0.');
    return null;
  }
  return n;
}

function clampQtyInput(el) {
  if (!el) return;
  const q = parsePositiveQty(el.value, { notify: false });
  el.value = q == null ? '1' : String(q);
}

async function loadTiendaPage() {
  await Promise.all([loadShopCollections(), loadTiendaProducts()]);
  updateShopHighlights();
  renderTiendaCart();
}

function updateShopHighlights() {
  const products = tiendaState.products || [];
  const meta = document.getElementById('shop-results-range');
  if (meta && products.length) {
    const n = tiendaState.filtered.length;
    meta.textContent = n
      ? `Mostrando 1–${n} de ${products.length} resultados`
      : `0 resultados de ${products.length}`;
  }
  initShopPriceSlider(products);
}

function initShopPriceSlider(products) {
  const slider = document.getElementById('shop-price-max');
  if (!slider || !products.length) return;
  const prices = products.map(p => Number((p.variant || {}).price || 0)).filter(n => n > 0);
  if (!prices.length) return;
  const max = Math.ceil(Math.max(...prices));
  slider.min = '0';
  slider.max = String(max);
  if (tiendaState.priceMax == null || tiendaState.priceMax > max) {
    tiendaState.priceMax = max;
    slider.value = String(max);
  }
  onShopPriceSlider();
}

function onShopPriceSlider() {
  const slider = document.getElementById('shop-price-max');
  const label = document.getElementById('shop-price-range-label');
  if (!slider || !label) return;
  const max = Number(slider.value || 0);
  tiendaState.priceMax = max;
  label.textContent = `Precio: ${shopMoney(0)} — ${shopMoney(max)}`;
}

async function loadShopCollections() {
  const nav = document.getElementById('shop-collections-nav');
  if (!nav) return;
  nav.innerHTML = '<button type="button" class="shop-collection-link" disabled>Cargando…</button>';
  try {
    const r = await fetch(API + '/shop/collections');
    const data = await r.json();
    if (!r.ok) throw new Error(data.message || 'Error al cargar colecciones');
    tiendaState.collections = data.collections || [];
    renderShopCollectionsNav();
  } catch (e) {
    nav.innerHTML = `<button type="button" class="shop-collection-link" disabled>Error: ${e.message}</button>`;
  }
}

function selectShopCollection(id) {
  tiendaState.collectionId = id;
  renderShopCollectionsNav();
  loadTiendaProducts();
}

function renderShopCollectionsNav() {
  const nav = document.getElementById('shop-collections-nav');
  if (!nav) return;
  const allCount = tiendaState.collections.reduce((s, c) => s + (c.product_count || 0), 0);
  let html = `<button type="button" class="shop-collection-link ${tiendaState.collectionId == null ? 'active' : ''}" onclick="selectShopCollection(null)">
    Todos <span>(${allCount})</span></button>`;
  html += tiendaState.collections.map(c =>
    `<button type="button" class="shop-collection-link ${tiendaState.collectionId === c.collection_id ? 'active' : ''}" onclick="selectShopCollection(${c.collection_id})">
      ${c.title} <span>(${c.product_count || 0})</span></button>`
  ).join('');
  nav.innerHTML = html;
  updateShopBulkActions();
}

function applyShopFilters() {
  filterShopProducts();
}

function sortShopProducts(list) {
  const mode = document.getElementById('shop-sort')?.value || 'default';
  const items = list.slice();
  if (mode === 'price-asc') {
    items.sort((a, b) => Number((a.variant || {}).price || 0) - Number((b.variant || {}).price || 0));
  } else if (mode === 'price-desc') {
    items.sort((a, b) => Number((b.variant || {}).price || 0) - Number((a.variant || {}).price || 0));
  } else if (mode === 'name-asc') {
    items.sort((a, b) => String(a.title || '').localeCompare(String(b.title || ''), 'es'));
  }
  return items;
}

function syncShopBulkQty(value) {
  const v = String(value ?? '');
  ['shop-bulk-qty', 'shop-bulk-qty-side'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = v;
  });
}

function updateShopBulkActions() {
  const wrap = document.getElementById('shop-bulk-add');
  const btn = document.getElementById('shop-bulk-btn');
  const sideActions = document.getElementById('shop-collection-bulk-actions');
  const sideHint = document.getElementById('shop-collection-bulk-hint');
  const sideBtn = document.getElementById('shop-bulk-btn-side');
  const collection = tiendaState.collections.find(c => c.collection_id === tiendaState.collectionId);
  const count = tiendaState.filtered.length;
  const show = tiendaState.collectionId != null && count > 0;
  const qty = parseInt(document.getElementById('shop-bulk-qty')?.value || document.getElementById('shop-bulk-qty-side')?.value, 10) || 1;
  const label = collection
    ? `Pedir ${collection.title} completa (${count} × ${qty})`
    : `Agregar colección completa (${count} productos × ${qty})`;

  if (wrap) wrap.hidden = !show;
  if (btn && show) {
    btn.textContent = label;
    btn.title = collection ? `Agregar todos los productos de ${collection.title}` : '';
  }
  if (sideActions) sideActions.hidden = !show;
  if (sideHint) sideHint.hidden = show;
  if (sideBtn && show) {
    sideBtn.textContent = label;
    sideBtn.title = btn?.title || '';
  }
}

async function loadTiendaProducts() {
  const grid = document.getElementById('tienda-grid');
  const meta = document.getElementById('shop-results-range');
  if (!grid) return;
  if (meta) meta.textContent = 'Cargando catálogo…';
  grid.innerHTML = '<div class="shop-cart-empty" style="grid-column:1/-1">Cargando productos…</div>';
  const q = new URLSearchParams({ limit: 100 });
  if (tiendaState.collectionId != null) q.set('collection_id', tiendaState.collectionId);
  let r;
  let data = {};
  try {
    r = await fetch(API + '/shop/products?' + q);
    data = await r.json().catch(() => ({}));
  } catch (_) {
    grid.innerHTML = '<div class="shop-cart-empty" style="grid-column:1/-1">No se pudo conectar con el servidor.</div>';
    if (meta) meta.textContent = 'Error de conexión';
    notifyErr('No se pudo cargar el catálogo. Revisa que el servidor esté en marcha.');
    return;
  }
  if (!r.ok) {
    grid.innerHTML = `<div class="shop-cart-empty" style="grid-column:1/-1">${data.message || 'Error al cargar productos.'}</div>`;
    if (meta) meta.textContent = 'Error al cargar';
    notifyErr(data.message || 'Error al cargar el catálogo.');
    return;
  }
  tiendaState.products = data.products || [];
  tiendaState.filtered = tiendaState.products.slice();
  filterShopProducts();
  updateShopHighlights();
}

function filterShopProducts() {
  const grid = document.getElementById('tienda-grid');
  const term = (document.getElementById('shop-search')?.value || '').trim().toLowerCase();
  const maxPrice = tiendaState.priceMax;
  let list = tiendaState.products.slice();
  if (term) {
    list = list.filter(p =>
      (p.title || '').toLowerCase().includes(term) ||
      (p.product_type || '').toLowerCase().includes(term) ||
      String(p.product_id).includes(term));
  }
  if (maxPrice != null) {
    list = list.filter(p => Number((p.variant || {}).price || 0) <= maxPrice);
  }
  tiendaState.filtered = sortShopProducts(list);
  if (!grid) return;
  if (!tiendaState.filtered.length) {
    grid.innerHTML = typeof opsEmpty === 'function'
      ? `<div style="grid-column:1/-1">${opsEmpty({
          title: 'Catálogo en preparación',
          hint: 'Pronto tendremos productos disponibles para ti. Vuelve a visitarnos.',
        })}</div>`
      : '<div class="shop-cart-empty" style="grid-column:1/-1">Catálogo en preparación. Vuelve pronto.</div>';
    return;
  }
  grid.innerHTML = tiendaState.filtered.map(p => {
    const v = p.variant || {};
    const img = p.image?.src;
    const compare = v.compare_at_price && v.compare_at_price > v.price;
    const vid = v.variant_id || p.product_id;
    const pid = p.product_id;
    return `
    <article class="shop-product-card shop-product-card--classic" data-product-id="${pid}">
      <div class="shop-product-media shop-product-media--clickable" role="button" tabindex="0"
        onclick="event.stopPropagation(); openProductDetail(${pid})" onkeydown="if(event.key==='Enter'){event.preventDefault();openProductDetail(${pid})}">
        ${img ? `<img src="${img}" alt="${p.image?.alt || p.title || ''}">` : '<div class="shop-product-media--empty" aria-hidden="true"></div>'}
        ${compare ? '<span class="shop-product-badge shop-product-badge--sale">¡Rebajado!</span>' : ''}
      </div>
      <div class="shop-product-body shop-product-body--classic">
        <button type="button" class="shop-product-title shop-product-title--link" onclick="event.stopPropagation(); openProductDetail(${pid})">${p.title}</button>
        <div class="shop-product-prices shop-product-prices--classic">
          ${compare ? `<span class="shop-compare">${shopMoney(v.compare_at_price)}</span>` : ''}
          <span class="shop-price">${shopMoney(v.price)}</span>
        </div>
        <button type="button" class="shop-widget-btn shop-product-details-btn" onclick="event.stopPropagation(); openProductDetail(${pid})">Ver detalles</button>
        <div class="shop-product-actions shop-product-actions--classic">
          <input type="number" min="1" step="1" value="1" id="qty-${vid}" onclick="event.stopPropagation()" oninput="clampQtyInput(this)" aria-label="Cantidad" />
          <button type="button" class="shop-widget-btn shop-widget-btn--primary" onclick="tiendaAddToCart(${vid})">Agregar</button>
        </div>
      </div>
    </article>`;
  }).join('');
  updateShopBulkActions();
  updateShopHighlights();
}

function tiendaAddProductToCart(prod, qty) {
  if (!prod || qty < 1) return;
  const v = prod.variant || {};
  const variantId = v.variant_id || prod.product_id;
  const price = Number(v.price || 0);
  const existing = tiendaState.cart.find(c => c.variant_id === variantId);
  if (existing) existing.quantity += qty;
  else {
    tiendaState.cart.push({
      variant_id: variantId,
      product_id: prod.product_id,
      title: prod.title,
      sku: v.sku,
      quantity: qty,
      price,
    });
  }
}

function tiendaAddToCart(variantId) {
  const qtyEl = document.getElementById('qty-' + variantId);
  const qty = parsePositiveQty(qtyEl?.value);
  if (qty == null) {
    if (qtyEl) clampQtyInput(qtyEl);
    return;
  }
  const prod = tiendaState.products.find(p => (p.variant?.variant_id || p.product_id) === variantId);
  if (!prod) return;
  tiendaAddProductToCart(prod, qty);
  renderTiendaCart();
  notifyOk('Producto agregado al carrito.');
}

async function tiendaAddCollectionToCart() {
  if (tiendaState.collectionId == null) {
    notifyWarn('Elige una colección en el panel izquierdo.');
    return;
  }
  const qty = parsePositiveQty(
    document.getElementById('shop-bulk-qty')?.value || document.getElementById('shop-bulk-qty-side')?.value
  );
  if (qty == null) return;
  const products = tiendaState.filtered.slice();
  if (!products.length) {
    notify('No hay productos visibles en esta colección.');
    return;
  }
  const collection = tiendaState.collections.find(c => c.collection_id === tiendaState.collectionId);
  const label = collection?.title || 'esta colección';
  const search = (document.getElementById('shop-search')?.value || '').trim();
  const scope = search
    ? `${products.length} productos visibles (filtro activo)`
    : `${products.length} productos de ${label}`;
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Agregar colección al carrito',
    message: `¿Agregar ${scope} al carrito con ${qty} unidad(es) de cada uno?`,
    confirmLabel: 'Agregar',
  });
  if (!ok) return;
  products.forEach(p => tiendaAddProductToCart(p, qty));
  renderTiendaCart();
}

function renderTiendaCart() {
  const el = document.getElementById('tienda-cart');
  const badge = document.getElementById('shop-cart-badge');
  const totalEl = document.getElementById('shop-cart-total');
  const btn = document.getElementById('shop-checkout-btn');
  const items = tiendaState.cart.reduce((s, c) => s + c.quantity, 0);
  const subtotal = tiendaState.cart.reduce((s, c) => s + c.price * c.quantity, 0);
  if (badge) badge.textContent = items;
  if (totalEl) totalEl.textContent = shopMoney(subtotal);
  if (btn) btn.disabled = !tiendaState.cart.length;
  if (!el) return;
  if (!tiendaState.cart.length) {
    el.innerHTML = '<div class="shop-cart-empty"><strong>Tu carrito está vacío</strong>Explora el catálogo y agrega los productos que necesitas.</div>';
    return;
  }
  el.innerHTML = tiendaState.cart.map(c => `
    <div class="shop-cart-line">
      <div class="shop-cart-line-info">
        <div class="shop-cart-line-title">${c.title}</div>
        <div class="shop-cart-line-meta">${c.sku || ''} × ${c.quantity}</div>
      </div>
      <div>
        <div class="shop-cart-line-price">${shopMoney(c.price * c.quantity)}</div>
        <button type="button" class="btn btn-ghost" style="padding:2px 6px;font-size:10px;margin-top:4px" onclick="tiendaRemoveFromCart(${c.variant_id})">Quitar</button>
      </div>
    </div>`).join('');
}

function tiendaRemoveFromCart(variantId) {
  tiendaState.cart = tiendaState.cart.filter(c => c.variant_id !== variantId);
  renderTiendaCart();
}

let productDetailState = { productId: null, variantId: null };
let productDetailLoading = false;

function escHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function closeProductDetail() {
  const m = document.getElementById('product-detail-modal');
  if (!m) return;
  m.hidden = true;
  m.setAttribute('aria-hidden', 'true');
  productDetailState = { productId: null, variantId: null };
}

function renderProductDetailRows(rows) {
  return rows.map(([label, value]) => `
    <div class="shop-detail-row">
      <span class="shop-detail-label">${label}</span>
      <span class="shop-detail-value">${value}</span>
    </div>`).join('');
}

function renderProductDetailModal(p) {
  const media = document.getElementById('prod-detail-media');
  const title = document.getElementById('prod-detail-title');
  const category = document.getElementById('prod-detail-category');
  const body = document.getElementById('prod-detail-body');
  if (!p || !body) return;

  const v = p.variant || {};
  const vid = v.variant_id || p.product_id;
  productDetailState = { productId: p.product_id, variantId: vid };

  if (title) title.textContent = p.name || p.title || 'Producto';
  if (category) {
    const bits = [p.category_name, p.collection_title].filter(Boolean);
    category.textContent = bits.length ? bits.join(' · ') : (p.product_type || 'Catálogo GLOBTRADE');
  }
  if (media) {
    const img = p.image?.src;
    media.innerHTML = img
      ? `<img src="${escHtml(img)}" alt="${escHtml(p.image?.alt || p.name || '')}">`
      : '<div class="shop-product-media--empty" style="min-height:220px"></div>';
  }

  const stock = v.inventory_quantity ?? '—';
  const vendorLoc = p.vendor_location ? ` (${p.vendor_location})` : '';
  const rows = [
    ['Nombre', p.name || p.title || '—'],
    ['Función principal', p.main_function || '—'],
    ['Peso', p.weight_kg != null ? `${Number(p.weight_kg).toFixed(2)} kg` : '—'],
    ['Proveedor', `${p.vendor_name || '—'}${vendorLoc}`],
    ['Categoría', p.category_name || p.product_type || '—'],
    ['Colección', p.collection_title || '—'],
    ['Código SKU', v.sku || vid],
    ['Precio unitario', shopMoney(p.unit_price ?? v.price)],
    ['Costo', shopMoney(p.unit_cost ?? v.cost)],
    ['Margen', p.margin_pct != null ? `${Number(p.margin_pct).toFixed(1)}%` : '—'],
    ['Existencias disponibles', String(stock)],
    ['Bodega', p.warehouse || 'Bodega General'],
    ['Línea catálogo', p.line != null ? String(p.line) : '—'],
  ];
  body.innerHTML = `
    ${p.description ? `<p class="shop-detail-desc">${escHtml(p.description)}</p>` : ''}
    <div class="shop-detail-grid">${renderProductDetailRows(rows.map(([k, val]) => [k, escHtml(val)]))}</div>`;

  const qtyEl = document.getElementById('prod-detail-qty');
  if (qtyEl) qtyEl.value = '1';
}

function findTiendaProduct(productId) {
  const id = Number(productId);
  return tiendaState.products.find(p => Number(p.product_id) === id)
    || tiendaState.filtered.find(p => Number(p.product_id) === id);
}

async function openProductDetail(productId) {
  if (productDetailLoading) return;
  productDetailLoading = true;

  const m = document.getElementById('product-detail-modal');
  const body = document.getElementById('prod-detail-body');
  if (!m || !body) {
    productDetailLoading = false;
    return;
  }

  m.hidden = false;
  m.setAttribute('aria-hidden', 'false');

  const cached = findTiendaProduct(productId);
  if (cached) {
    renderProductDetailModal(cached);
    productDetailLoading = false;
    return;
  }

  const title = document.getElementById('prod-detail-title');
  const category = document.getElementById('prod-detail-category');
  const media = document.getElementById('prod-detail-media');
  if (title) title.textContent = 'Cargando…';
  if (category) category.textContent = '';
  if (media) media.innerHTML = '<div class="shop-product-media--empty" style="min-height:220px"></div>';
  body.innerHTML = '<p class="modal-sub">Cargando ficha del producto…</p>';

  try {
    const r = await fetch(`${API}/shop/products/${productId}`);
    let data = {};
    try {
      data = await r.json();
    } catch {
      data = {};
    }
    if (!r.ok || !data.product) {
      closeProductDetail();
      notifyErr(data.message || 'No se pudo cargar el producto.');
      return;
    }
    renderProductDetailModal(data.product);
  } catch (_) {
    closeProductDetail();
    notifyErr('No se pudo conectar con el servidor.');
  } finally {
    productDetailLoading = false;
  }
}

function tiendaAddFromDetail() {
  const vid = productDetailState.variantId;
  if (!vid) return;
  const qtyEl = document.getElementById('prod-detail-qty');
  const qty = parsePositiveQty(qtyEl?.value);
  if (qty == null) {
    if (qtyEl) clampQtyInput(qtyEl);
    return;
  }
  const prod = tiendaState.products.find(p =>
    Number(p.product_id) === Number(productDetailState.productId)
    || (p.variant?.variant_id || p.product_id) === vid);
  if (!prod) {
    notifyWarn('Producto no disponible en el listado actual.');
    return;
  }
  tiendaAddProductToCart(prod, qty);
  renderTiendaCart();
  notifyOk('Producto agregado al carrito.');
  closeProductDetail();
}

window.openProductDetail = openProductDetail;
window.closeProductDetail = closeProductDetail;
window.tiendaAddFromDetail = tiendaAddFromDetail;

function isAssistedPurchase() {
  return !!(window._authUser && window._authUser.role !== 'cliente');
}

function openSolicitudModal() {
  if (!tiendaState.cart.length) { notifyWarn('Agrega productos al carrito.'); return; }
  if (!window._authUser) {
    notifyWarn('Inicia sesión para solicitar la compra. Así verás el pedido en Mis pedidos.');
    if (typeof openLoginModal === 'function') openLoginModal();
    return;
  }
  if (!hasPermission('shop.checkout')) {
    notifyWarn('Tu rol no permite solicitar compras en la vitrina.');
    return;
  }
  loadTiendaMasterSelects();
  refreshShippingQuote();
  const user = window._authUser;
  const assisted = isAssistedPurchase();
  const n = document.getElementById('sol-client-name');
  const e = document.getElementById('sol-client-email');
  const channelWrap = document.getElementById('sol-channel-wrap');
  const lead = document.getElementById('sol-modal-lead');
  if (n) {
    n.value = user.name || '';
    n.readOnly = !assisted;
  }
  if (e) {
    e.value = user.email || '';
    e.readOnly = !assisted;
  }
  if (channelWrap) channelWrap.hidden = !assisted;
  if (lead) {
    lead.textContent = assisted
      ? 'Pedido asistido: indica el cliente y el canal. El pedido quedará registrado a su nombre.'
      : 'Confirma destino, país y contacto. El total incluye envío estimado para pedidos online.';
  }
  const destWrap = document.getElementById('sol-destination-wrap');
  if (destWrap) destWrap.hidden = assisted && (parseInt(document.getElementById('sol-channel-id')?.value, 10) || 1) !== 1;
  document.getElementById('solicitud-modal').hidden = false;
}

function closeSolicitudModal() {
  document.getElementById('solicitud-modal').hidden = true;
}

function checkoutSubtotal() {
  return tiendaState.cart.reduce((s, c) => s + c.price * c.quantity, 0);
}

async function refreshShippingQuote() {
  tiendaState.shippingCost = 0;
  tiendaState.shippingRegion = '';
  const assisted = isAssistedPurchase();
  const channelSel = document.getElementById('sol-channel-id');
  const channelId = assisted ? (parseInt(channelSel?.value, 10) || 1) : 1;
  const isOnline = channelId === 1;
  if (!isOnline || !tiendaState.cart.length) {
    updateCheckoutSummary();
    return;
  }
  const country_id = parseInt(document.getElementById('sol-country-id')?.value, 10);
  if (!country_id) {
    updateCheckoutSummary();
    return;
  }
  try {
    const r = await fetch(API + '/shop/shipping/quote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        country_id,
        lines: tiendaState.cart.map(c => ({ variant_id: c.variant_id, quantity: c.quantity })),
      }),
    });
    const data = await r.json();
    if (r.ok) {
      tiendaState.shippingCost = Number(data.shipping_cost || 0);
      tiendaState.shippingRegion = data.region_name || '';
    }
  } catch (_) { /* ignore */ }
  updateCheckoutSummary();
}

function updateCheckoutSummary() {
  const sub = checkoutSubtotal();
  const disc = Number(tiendaState.discountAmount || 0);
  const ship = Number(tiendaState.shippingCost || 0);
  const total = Math.max(sub - disc + ship, 0);
  const el = document.getElementById('sol-checkout-summary');
  if (el) {
    const assisted = isAssistedPurchase();
    const channelSel = document.getElementById('sol-channel-id');
    const channelId = assisted ? (parseInt(channelSel?.value, 10) || 1) : 1;
    const shipLine = channelId === 1
      ? ` · Envío: <strong>${shopMoney(ship)}</strong>${tiendaState.shippingRegion ? ` <span style="color:var(--muted);font-weight:400">(${tiendaState.shippingRegion})</span>` : ''}`
      : '';
    el.innerHTML = `Subtotal: <strong>${shopMoney(sub)}</strong>`
      + (disc ? ` · Descuento: <strong>-${shopMoney(disc)}</strong>` : '')
      + shipLine
      + ` · Total: <strong>${shopMoney(total)}</strong>`;
  }
}

async function applyCheckoutCoupon() {
  const code = (document.getElementById('sol-coupon')?.value || '').trim();
  if (!code) { tiendaState.discountAmount = 0; tiendaState.discountCode = ''; updateCheckoutSummary(); return; }
  const r = await fetch(API + '/shop/coupon/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, subtotal: checkoutSubtotal() }),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Cupón inválido'); return; }
  tiendaState.discountAmount = data.discount_amount || 0;
  tiendaState.discountCode = data.code || code;
  updateCheckoutSummary();
  notifyOk('Cupón aplicado.');
}

async function submitSolicitud() {
  if (!window._authUser) {
    notifyWarn('Inicia sesión para completar la compra.');
    return;
  }
  const assisted = isAssistedPurchase();
  const name = (document.getElementById('sol-client-name').value || window._authUser.name || '').trim();
  const email = (document.getElementById('sol-client-email').value || window._authUser.email || '').trim();
  if (!name || !email) { notifyWarn('Nombre y correo del cliente son obligatorios.'); return; }
  for (const c of tiendaState.cart) {
    if (!c.quantity || c.quantity < 1) {
      notifyWarn('Hay productos con cantidad inválida en el carrito.');
      return;
    }
  }
  const phone = document.getElementById('sol-client-phone').value.trim();
  const country_id = parseInt(document.getElementById('sol-country-id').value, 10);
  const destination = (document.getElementById('sol-shipping-destination')?.value || '').trim();
  const channelSel = document.getElementById('sol-channel-id');
  const channel_id = assisted
    ? (parseInt(channelSel?.value, 10) || 1)
    : 1;
  if (channel_id === 1 && !assisted && !destination) {
    notifyWarn('Indica el destino de entrega (ciudad, dirección o ruta).');
    return;
  }
  const notes = document.getElementById('sol-notes').value.trim();
  const body = {
    name, email, phone, country_id, channel_id, notes,
    client_name: name,
    client_email: email,
    shipping_destination: destination || undefined,
    destination: destination || undefined,
    discount_code: tiendaState.discountCode || '',
    lines: tiendaState.cart.map(c => ({ variant_id: c.variant_id, quantity: c.quantity })),
  };
  const r = await fetch(API + '/shop/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error al solicitar la compra'); return; }
  tiendaState.cart = [];
  tiendaState.discountAmount = 0;
  tiendaState.discountCode = '';
  tiendaState.shippingCost = 0;
  renderTiendaCart();
  closeSolicitudModal();
  notifyOk(data.message || 'Pedido registrado. Revísalo en Mis pedidos.');
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
  if (typeof refreshVentasBadge === 'function') refreshVentasBadge();
  const misBtn = document.querySelector('[data-page=mis-pedidos]');
  if (misBtn) showPage('mis-pedidos', misBtn);
}

async function loadTiendaMasterSelects() {
  try {
    const [paises, canales] = await Promise.all([
      fetch(API + '/shop/countries?limit=500').then(r => r.json()),
      fetch(API + '/master/dim_canal?limit=20').then(r => r.json()),
    ]);
    const countrySel = document.getElementById('sol-country-id');
    const countries = paises.countries || paises.rows || [];
    if (countrySel && countries.length) {
      const prev = countrySel.value;
      countrySel.innerHTML = countries.map(p =>
        `<option value="${p.country_id}">${p.name}</option>`).join('');
      if (prev) countrySel.value = prev;
      countrySel.onchange = () => refreshShippingQuote();
    }
    const chSel = document.getElementById('sol-channel-id');
    if (chSel && (chSel.options.length <= 1 || isAssistedPurchase())) {
      const rows = canales.rows || [];
      if (rows.length) {
        chSel.innerHTML = rows.map(c =>
          `<option value="${c.channel_id}">${c.name}</option>`).join('');
        const online = rows.find(c => String(c.name || '').toLowerCase() === 'online');
        if (online) chSel.value = String(online.channel_id);
        chSel.onchange = () => {
          const destWrap = document.getElementById('sol-destination-wrap');
          if (destWrap) destWrap.hidden = parseInt(chSel.value, 10) !== 1;
          refreshShippingQuote();
        };
      }
    }
  } catch (e) { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', () => {
  loadTiendaMasterSelects();
  const destInput = document.getElementById('sol-shipping-destination');
  if (destInput) destInput.addEventListener('input', () => { /* destino validado al enviar */ });
});
