/* Storefront B2B — colecciones, variantes, carrito, checkout */
let tiendaState = {
  collections: [],
  products: [],
  filtered: [],
  collectionId: null,
  cart: [],
  discountCode: '',
  discountAmount: 0,
};

function shopMoney(n) {
  return '$' + Number(n || 0).toFixed(2);
}

async function loadTiendaPage() {
  await loadShopStats();
  await loadShopCollections();
  await loadTiendaProducts();
  renderTiendaCart();
}

async function loadShopStats() {
  try {
    const [stats, summary] = await Promise.all([
      fetch(API + '/shop/stats').then(r => r.json()),
      fetch(API + '/summary').then(r => r.json()).catch(() => ({})),
    ]);
    const counts = stats.counts || {};
    const total = Object.keys(counts).length;
    const filled = Object.values(counts).filter(n => n > 0).length;
    const products = counts.products || 0;
    const rev = summary.total_revenue;
    const revEl = document.getElementById('shop-float-revenue');
    const prodEl = document.getElementById('shop-float-products');
    const tabEl = document.getElementById('shop-float-tables');
    if (revEl && rev != null) revEl.textContent = '$' + Number(rev).toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (prodEl) prodEl.textContent = String(products);
    if (tabEl) tabEl.textContent = `${filled}/${total}`;
  } catch (e) { /* ignore */ }
}

async function loadShopCollections() {
  const nav = document.getElementById('shop-collections-nav');
  if (!nav) return;
  nav.innerHTML = '<button type="button" class="shop-collection-btn">Cargando…</button>';
  try {
    const r = await fetch(API + '/shop/collections');
    const data = await r.json();
    if (!r.ok) throw new Error(data.message || 'Error al cargar colecciones');
    tiendaState.collections = data.collections || [];
    renderShopCollectionsNav();
  } catch (e) {
    nav.innerHTML = `<button type="button" class="shop-collection-btn" disabled>Error: ${e.message}</button>`;
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
  let html = `<button type="button" class="shop-collection-btn ${tiendaState.collectionId == null ? 'active' : ''}" onclick="selectShopCollection(null)">
    Todos los productos <span class="shop-collection-count">${allCount}</span></button>`;
  html += tiendaState.collections.map(c =>
    `<button type="button" class="shop-collection-btn ${tiendaState.collectionId === c.collection_id ? 'active' : ''}" onclick="selectShopCollection(${c.collection_id})">
      ${c.title} <span class="shop-collection-count">${c.product_count || 0}</span></button>`
  ).join('');
  nav.innerHTML = html;
  updateShopBulkActions();
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
  const meta = document.getElementById('shop-products-meta');
  if (!grid) return;
  grid.innerHTML = '<div class="shop-cart-empty" style="grid-column:1/-1">Cargando productos…</div>';
  const q = new URLSearchParams({ limit: 100 });
  if (tiendaState.collectionId != null) q.set('collection_id', tiendaState.collectionId);
  const r = await fetch(API + '/shop/products?' + q);
  const data = await r.json();
  tiendaState.products = data.products || [];
  tiendaState.filtered = tiendaState.products.slice();
  if (meta) meta.textContent = `${data.total || 0} productos en catálogo`;
  filterShopProducts();
}

function filterShopProducts() {
  const grid = document.getElementById('tienda-grid');
  const term = (document.getElementById('shop-search')?.value || '').trim().toLowerCase();
  tiendaState.filtered = term
    ? tiendaState.products.filter(p =>
        (p.title || '').toLowerCase().includes(term) ||
        (p.product_type || '').toLowerCase().includes(term) ||
        String(p.product_id).includes(term))
    : tiendaState.products.slice();
  if (!grid) return;
  if (!tiendaState.filtered.length) {
    grid.innerHTML = typeof opsEmpty === 'function'
      ? `<div style="grid-column:1/-1">${opsEmpty({
          title: 'Catálogo vacío',
          hint: 'Un administrador debe sincronizar el catálogo en Maestros para publicar productos.',
          ctaLabel: 'Ir a Maestros',
          ctaOnclick: "showPage('datos')",
        })}</div>`
      : '<div class="shop-cart-empty" style="grid-column:1/-1">Catálogo vacío. Sincroniza en Maestros.</div>';
    return;
  }
  grid.innerHTML = tiendaState.filtered.map(p => {
    const v = p.variant || {};
    const img = p.image?.src;
    const compare = v.compare_at_price && v.compare_at_price > v.price;
    const vid = v.variant_id || p.product_id;
    const qty = v.inventory_quantity ?? '—';
    return `
    <article class="shop-product-card">
      <div class="shop-product-media">
        ${img ? `<img src="${img}" alt="${p.image?.alt || p.title || ''}">` : '<div class="shop-product-media--empty" aria-hidden="true"></div>'}
        ${compare ? '<span class="shop-product-badge">Oferta</span>' : ''}
      </div>
      <div class="shop-product-body">
        <div class="shop-product-vendor">${p.product_type || 'General'}</div>
        <div class="shop-product-title">${p.title}</div>
        <div class="shop-product-prices">
          <span class="shop-price">${shopMoney(v.price)}</span>
          ${compare ? `<span class="shop-compare">${shopMoney(v.compare_at_price)}</span>` : ''}
        </div>
        <div style="font-size:0.7rem;color:var(--shop-muted);margin-top:4px">SKU ${v.sku || vid} · Stock ${qty}</div>
        <div class="shop-product-actions">
          <input type="number" min="1" value="1" id="qty-${vid}" />
          <button type="button" class="btn btn-primary" onclick="tiendaAddToCart(${vid})">Agregar</button>
        </div>
      </div>
    </article>`;
  }).join('');
  updateShopBulkActions();
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
  const qty = parseInt(qtyEl?.value, 10) || 1;
  const prod = tiendaState.products.find(p => (p.variant?.variant_id || p.product_id) === variantId);
  if (!prod) return;
  tiendaAddProductToCart(prod, qty);
  renderTiendaCart();
}

function tiendaAddCollectionToCart() {
  if (tiendaState.collectionId == null) {
    alert('Elige una colección en el panel izquierdo.');
    return;
  }
  const qty = parseInt(document.getElementById('shop-bulk-qty')?.value, 10) || 1;
  if (qty < 1) {
    alert('Indica una cantidad válida por producto.');
    return;
  }
  const products = tiendaState.filtered.slice();
  if (!products.length) {
    alert('No hay productos visibles en esta colección.');
    return;
  }
  const collection = tiendaState.collections.find(c => c.collection_id === tiendaState.collectionId);
  const label = collection?.title || 'esta colección';
  const search = (document.getElementById('shop-search')?.value || '').trim();
  const scope = search
    ? `${products.length} productos visibles (filtro activo)`
    : `${products.length} productos de ${label}`;
  if (!confirm(`¿Agregar ${scope} al carrito con ${qty} unidad(es) de cada uno?`)) return;
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
    el.innerHTML = '<div class="shop-cart-empty"><strong>Carrito vacío</strong>Elige productos del catálogo o una colección completa.</div>';
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

function isAssistedPurchase() {
  return !!(window._authUser && (
    window._authUser.role === 'administrador'
    || (typeof hasPermission === 'function' && hasPermission('ventas.manage'))
  ));
}

function openSolicitudModal() {
  if (!tiendaState.cart.length) { alert('Agrega productos al carrito.'); return; }
  if (!window._authUser) {
    alert('Inicia sesión para solicitar la compra. Así verás el pedido en Mis pedidos.');
    if (typeof openLoginModal === 'function') openLoginModal();
    return;
  }
  if (!hasPermission('shop.checkout')) {
    alert('Tu rol no permite solicitar compras en la vitrina.');
    return;
  }
  loadTiendaMasterSelects();
  updateCheckoutSummary();
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
      ? 'Pedido asistido: indica el cliente fijo y el canal. Se creará una solicitud comercial a su nombre.'
      : 'Confirma tus datos. Se creará una solicitud comercial para revisar y confirmar la venta.';
  }
  document.getElementById('solicitud-modal').hidden = false;
}

function closeSolicitudModal() {
  document.getElementById('solicitud-modal').hidden = true;
}

function checkoutSubtotal() {
  return tiendaState.cart.reduce((s, c) => s + c.price * c.quantity, 0);
}

function updateCheckoutSummary() {
  const sub = checkoutSubtotal();
  const disc = Number(tiendaState.discountAmount || 0);
  const el = document.getElementById('sol-checkout-summary');
  if (el) {
    el.innerHTML = `Subtotal: <strong>${shopMoney(sub)}</strong>`
      + (disc ? ` · Descuento: <strong>-${shopMoney(disc)}</strong>` : '')
      + ` · Total: <strong>${shopMoney(Math.max(sub - disc, 0))}</strong>`;
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
  if (!r.ok) { alert(data.message || 'Cupón inválido'); return; }
  tiendaState.discountAmount = data.discount_amount || 0;
  tiendaState.discountCode = data.code || code;
  updateCheckoutSummary();
}

async function submitSolicitud() {
  if (!window._authUser) {
    alert('Inicia sesión para completar la compra.');
    return;
  }
  const assisted = isAssistedPurchase();
  const name = (document.getElementById('sol-client-name').value || window._authUser.name || '').trim();
  const email = (document.getElementById('sol-client-email').value || window._authUser.email || '').trim();
  if (!name || !email) { alert('Nombre y correo del cliente son obligatorios.'); return; }
  const phone = document.getElementById('sol-client-phone').value.trim();
  const country_id = parseInt(document.getElementById('sol-country-id').value, 10);
  const channelSel = document.getElementById('sol-channel-id');
  const channel_id = assisted
    ? (parseInt(channelSel?.value, 10) || 1)
    : 1; // Online por defecto para el cliente
  const notes = document.getElementById('sol-notes').value.trim();
  const body = {
    name, email, phone, country_id, channel_id, notes,
    client_name: name,
    client_email: email,
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
  if (!r.ok) { alert(data.message || 'Error al solicitar la compra'); return; }
  tiendaState.cart = [];
  tiendaState.discountAmount = 0;
  tiendaState.discountCode = '';
  renderTiendaCart();
  closeSolicitudModal();
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
    }
    const chSel = document.getElementById('sol-channel-id');
    if (chSel && (chSel.options.length <= 1 || isAssistedPurchase())) {
      const rows = canales.rows || [];
      if (rows.length) {
        chSel.innerHTML = rows.map(c =>
          `<option value="${c.channel_id}">${c.name}</option>`).join('');
        const online = rows.find(c => String(c.name || '').toLowerCase() === 'online');
        if (online) chSel.value = String(online.channel_id);
      }
    }
  } catch (e) { /* ignore */ }
}

document.addEventListener('DOMContentLoaded', () => { loadTiendaMasterSelects(); });
