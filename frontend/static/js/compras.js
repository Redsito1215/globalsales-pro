/* Q4 Compras — proveedores, inventario, OCs */
let comprasTab = 'inventario';
let vendorGeoState = { regions: [], countries: [], regionId: null, countryId: null };

const REGION_LABELS = {
  'South America': 'América del Sur',
  'North America': 'América del Norte',
  'Europe': 'Europa',
  'Asia': 'Asia',
  'Africa': 'África',
  'Oceania': 'Oceanía',
  'Central America and the Caribbean': 'Centroamérica y Caribe',
};

function regionLabel(name) {
  return REGION_LABELS[name] || name || '—';
}

function vendorGeoDisplay(v) {
  const parts = [];
  if (v.region_name) parts.push(regionLabel(v.region_name));
  if (v.country) parts.push(v.country);
  return parts.length ? parts.join(' · ') : '—';
}

function comprasEsc(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

async function ensureVendorGeoMasters() {
  if (vendorGeoState.regions.length) return;
  try {
    const [regR, coR] = await Promise.all([
      fetch(`${API}/master/dim_region?limit=50`, { credentials: 'same-origin' }),
      fetch(`${API}/shop/countries?limit=500`, { credentials: 'same-origin' }),
    ]);
    const regData = await regR.json();
    const coData = await coR.json();
    vendorGeoState.regions = (regData.rows || []).sort((a, b) =>
      regionLabel(a.name).localeCompare(regionLabel(b.name), 'es'));
    vendorGeoState.countries = coData.countries || coData.rows || [];
  } catch { /* ignore */ }
}

function renderVendorRegionTable() {
  const body = document.getElementById('vend-region-body');
  if (!body) return;
  body.innerHTML = (vendorGeoState.regions || []).map(r => {
    const sel = Number(vendorGeoState.regionId) === Number(r.region_id);
    return `<tr class="geo-pick-row${sel ? ' geo-pick-row--active' : ''}" onclick="selectVendorRegion(${r.region_id})">
      <td>${regionLabel(r.name)}</td>
      <td><span class="table-sub">${r.name || ''}</span></td>
    </tr>`;
  }).join('') || '<tr><td colspan="2">Sin continentes en maestros</td></tr>';
  renderVendorCountryTable();
  updateVendorGeoSummary();
}

function renderVendorCountryTable() {
  const body = document.getElementById('vend-country-body');
  if (!body) return;
  const rid = vendorGeoState.regionId;
  if (!rid) {
    body.innerHTML = '<tr><td colspan="2">Elige un continente arriba</td></tr>';
    updateVendorGeoSummary();
    return;
  }
  const list = vendorGeoState.countries.filter(c => Number(c.region_id) === Number(rid));
  body.innerHTML = list.map(c => {
    const sel = Number(vendorGeoState.countryId) === Number(c.country_id);
    return `<tr class="geo-pick-row${sel ? ' geo-pick-row--active' : ''}" onclick="selectVendorCountry(${c.country_id})">
      <td>${c.name}</td>
      <td>${c.country_id}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="2">Sin países para este continente</td></tr>';
  updateVendorGeoSummary();
}

function updateVendorGeoSummary() {
  const el = document.getElementById('vend-geo-summary');
  if (!el) return;
  const reg = vendorGeoState.regions.find(r => Number(r.region_id) === Number(vendorGeoState.regionId));
  const co = vendorGeoState.countries.find(c => Number(c.country_id) === Number(vendorGeoState.countryId));
  if (reg && co) el.textContent = `Seleccionado: ${regionLabel(reg.name)} · ${co.name}`;
  else if (reg) el.textContent = `Continente: ${regionLabel(reg.name)} — elige un país`;
  else el.textContent = 'Elige continente y país del proveedor';
}

function setVendorGeo(regionId, countryId) {
  vendorGeoState.regionId = regionId ? Number(regionId) : null;
  vendorGeoState.countryId = countryId ? Number(countryId) : null;
  renderVendorRegionTable();
}

function selectVendorRegion(regionId) {
  vendorGeoState.regionId = Number(regionId);
  vendorGeoState.countryId = null;
  renderVendorRegionTable();
}

function selectVendorCountry(countryId) {
  vendorGeoState.countryId = Number(countryId);
  const c = vendorGeoState.countries.find(x => Number(x.country_id) === Number(countryId));
  if (c) vendorGeoState.regionId = Number(c.region_id);
  renderVendorRegionTable();
}

function renderWarehouseBanner(warehouse) {
  const banner = document.getElementById('compras-warehouse-banner');
  const nameEl = document.getElementById('compras-warehouse-name');
  const metaEl = document.getElementById('compras-warehouse-meta');
  if (!banner) return;
  const wh = warehouse || { name: 'Bodega General', address: 'Ubicación única' };
  if (nameEl) nameEl.textContent = wh.name || 'Bodega General';
  if (metaEl) {
    metaEl.textContent = wh.address || `${wh.code || 'BG-01'} · ubicación única · todo el stock se almacena aquí`;
  }
  banner.hidden = false;
}

function poStatusBadge(st) {
  const map = {
    borrador: 'badge badge--warn',
    enviada: 'badge badge--info',
    parcial: 'badge badge--warn',
    recibida: 'badge badge--ok',
    devuelta_parcial: 'badge badge--warn',
    devuelta: 'badge badge--danger',
    cancelada: 'badge badge--danger',
  };
  return `<span class="${map[st] || 'badge'}">${st || '—'}</span>`;
}

function toast(msg, type) {
  notify(msg, type || 'info');
}

async function loadComprasPage() {
  if (!window._authUser || !hasPermission('compras.manage')) {
    const root = document.getElementById('compras-root');
    if (root) {
      root.innerHTML = typeof opsEmpty === 'function'
        ? opsEmpty({ title: 'Sin acceso', hint: 'Solo personal con permiso de compras puede usar este módulo.' })
        : '<p class="catalog-empty">Solo personal con permiso de compras puede usar este módulo.</p>';
    }
    return;
  }
  const pref = window._comprasPrefill || null;
  if (pref) {
    if (pref.lowOnly) {
      const low = document.getElementById('compras-inv-low');
      if (low) low.checked = true;
      comprasTab = 'inventario';
    }
    if (pref.tab) comprasTab = pref.tab;
  }
  showComprasTab(comprasTab);
  if (pref && pref.tab === 'ocs') {
    await applyComprasPoPrefill(pref);
  }
  window._comprasPrefill = null;
}

function showComprasTab(tab) {
  comprasTab = tab;
  document.querySelectorAll('.compras-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.compras-panel').forEach(p => { p.hidden = p.id !== 'compras-panel-' + tab; });
  if (tab === 'inventario') loadComprasInventario();
  if (tab === 'proveedores') loadComprasProveedores();
  if (tab === 'requisiciones') loadComprasRequisitions();
  if (tab === 'ocs') loadComprasOCs();
  if (tab === 'caja') loadComprasCaja();
  if (tab === 'merma') loadComprasMerma();
}

async function applyComprasPoPrefill(pref) {
  await fillPoVendorSelect();
  await fillPoVariantSelect();
  const vendorEl = document.getElementById('po-vendor');
  const variantEl = document.getElementById('po-variant');
  const qtyEl = document.getElementById('po-qty');
  const costEl = document.getElementById('po-cost');
  if (variantEl && pref.variant_id) {
    if (![...variantEl.options].some(o => Number(o.value) === Number(pref.variant_id))) {
      const opt = document.createElement('option');
      opt.value = String(pref.variant_id);
      opt.textContent = `Variante ${pref.variant_id}`;
      variantEl.appendChild(opt);
    }
    variantEl.value = String(pref.variant_id);
  }
  if (vendorEl && pref.vendor_id) vendorEl.value = String(pref.vendor_id);
  if (qtyEl) qtyEl.value = String(pref.quantity || 10);
  if (costEl && pref.unit_cost != null) costEl.value = String(pref.unit_cost);
  const hint = document.getElementById('po-prefill-hint');
  if (hint) {
    hint.hidden = false;
    hint.textContent = 'Formulario precargado desde Decisiones (stock bajo). Revisa y crea la OC en borrador.';
  }
}

function renderComprasChips(invRows, poRows) {
  const chips = document.getElementById('compras-chips');
  if (!chips) return;
  const thr = parseInt(document.getElementById('compras-inv-thr')?.value || '20', 10);
  const low = (invRows || []).filter(r => Number(r.inventory_quantity || 0) <= thr).length;
  const draft = (poRows || []).filter(p => p.status === 'borrador').length;
  const sent = (poRows || []).filter(p => p.status === 'enviada' || p.status === 'parcial').length;
  const done = (poRows || []).filter(p => p.status === 'recibida').length;
  chips.innerHTML = `
    <span class="ops-chip ${low ? 'ops-chip--danger' : ''}"><span>Existencias bajas</span><strong>${low}</strong></span>
    <span class="ops-chip ops-chip--warn"><span>OC borrador</span><strong>${draft}</strong></span>
    <span class="ops-chip"><span>OC en tránsito</span><strong>${sent}</strong></span>
    <span class="ops-chip ops-chip--ok"><span>OC recibidas</span><strong>${done}</strong></span>`;
}

async function refreshComprasChips() {
  try {
    const thr = document.getElementById('compras-inv-thr')?.value || '20';
    const [invR, poR] = await Promise.all([
      fetch(`${API}/compras/inventory?limit=100&low_only=1&threshold=${encodeURIComponent(thr)}`, { credentials: 'same-origin' }),
      fetch(`${API}/compras/purchase-orders?limit=40`, { credentials: 'same-origin' }),
    ]);
    const inv = await invR.json().catch(() => ({}));
    const po = await poR.json().catch(() => ({}));
    renderComprasChips(inv.items || [], po.orders || []);
  } catch { /* ignore */ }
}

async function loadComprasInventario() {
  const body = document.getElementById('compras-inv-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="11">Cargando…</td></tr>';
  const q = new URLSearchParams({ limit: 100 });
  const term = (document.getElementById('compras-inv-q')?.value || '').trim();
  const low = document.getElementById('compras-inv-low')?.checked;
  if (term) q.set('q', term);
  if (low) q.set('low_only', '1');
  q.set('threshold', document.getElementById('compras-inv-thr')?.value || '20');
  const r = await fetch(API + '/compras/inventory?' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(11, { title: 'Error al cargar', hint: data.message || 'No se pudo cargar inventario' })
      : `<tr><td colspan="11">${data.message || 'Error al procesar'}</td></tr>`;
    return;
  }
  renderWarehouseBanner(data.warehouse);
  const rows = data.items || [];
  refreshComprasChips();
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(11, {
          title: 'Sin referencias',
          hint: 'Ejecuta Sincronizar catálogo en Maestros para generar variantes e inventario.',
          ctaLabel: 'Ir a Maestros',
          ctaOnclick: "showGestion('dim_producto')",
        })
      : '<tr><td colspan="11">Sin códigos SKU. Ejecuta Sincronizar catálogo en Maestros.</td></tr>';
    return;
  }
  const whName = (data.warehouse && data.warehouse.name) || 'Bodega General';
  const thr = parseInt(document.getElementById('compras-inv-thr')?.value || '20', 10);
  body.innerHTML = rows.map(row => {
    const qty = Number(row.inventory_quantity || 0);
    const sug = Math.max(thr - qty, 10);
    const lowBadge = qty <= thr ? '<span class="badge badge--danger">Bajo</span>' : '<span class="badge badge--ok">Correcto</span>';
    return `<tr>
      <td>${row.variant_id}</td>
      <td>${row.title}<br><span class="table-sub">${row.sku || ''}</span></td>
      <td><strong>${qty}</strong> ${lowBadge}</td>
      <td>${Number(row.committed || 0)}</td>
      <td>${Number(row.damaged || 0)}</td>
      <td>${Number(row.in_transit || 0)}</td>
      <td>${Number(row.minimum_stock || 0)}</td>
      <td><strong>${Number(row.reorder_suggestion || 0)}</strong></td>
      <td>$${Number(row.price || 0).toFixed(2)}</td>
      <td>$${Number(row.cost || 0).toFixed(2)}</td>
      <td style="white-space:nowrap">
        <input type="number" id="inv-set-${row.variant_id}" value="${qty}" style="width:70px" />
        <button type="button" class="btn btn-ghost btn-ops" onclick="saveStock(${row.variant_id})">Guardar</button>
        <button type="button" class="btn btn-ghost btn-ops" onclick="physicalCount(${row.variant_id},${qty})">Conteo</button>
        <button type="button" class="btn btn-ghost btn-ops" onclick="editInventoryPolicy(${row.variant_id},${Number(row.minimum_stock || 0)},${Number(row.reorder_target || 0)})">Mínimos</button>
        <button type="button" class="btn btn-ghost btn-ops" onclick="showInventoryKardex(${row.variant_id},'${String(row.sku || '').replace(/'/g, '')}')">Kardex</button>
        <button type="button" class="btn btn-primary btn-ops" onclick="quickPOFromStock(${row.variant_id},${row.vendor_id || 0},${Number(row.cost || 0)},${Number(row.reorder_suggestion || sug)})">OC</button>
      </td>
    </tr>`;
  }).join('');
}

async function quickPOFromStock(variantId, vendorId, unitCost, qty) {
  window._comprasPrefill = {
    tab: 'ocs',
    variant_id: variantId,
    vendor_id: vendorId || null,
    unit_cost: unitCost || 0,
    quantity: qty || 10,
  };
  showComprasTab('ocs');
  await applyComprasPoPrefill(window._comprasPrefill);
  window._comprasPrefill = null;
}

async function saveStock(variantId) {
  const val = parseInt(document.getElementById('inv-set-' + variantId)?.value, 10);
  if (Number.isNaN(val) || val < 0) { toast('Cantidad inválida', 'warn'); return; }
  if (typeof opsPrompt !== 'function') { toast('No se pudo abrir el formulario.', 'danger'); return; }
  const reason = await opsPrompt({
    title: 'Ajustar inventario',
    message: 'Este cambio quedará registrado en auditoría.',
    label: 'Motivo del ajuste',
    confirmLabel: 'Guardar ajuste',
    validate: val => val.trim().length < 8 ? 'Escribe un motivo de al menos 8 caracteres.' : null,
  });
  if (reason == null) return;
  const r = await fetch(`${API}/compras/inventory/${variantId}`, {
    method: 'PATCH', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ available: val, reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('Existencias actualizadas', 'ok');
  loadComprasInventario();
}

async function bumpStock(variantId, delta) {
  if (typeof opsPrompt !== 'function') { toast('No se pudo abrir el formulario.', 'danger'); return; }
  const reason = await opsPrompt({
    title: 'Ajustar inventario',
    message: `Se aplicará un ajuste de ${delta > 0 ? '+' : ''}${delta} unidad(es).`,
    label: 'Motivo del ajuste',
    confirmLabel: 'Aplicar ajuste',
    validate: val => val.trim().length < 8 ? 'Escribe un motivo de al menos 8 caracteres.' : null,
  });
  if (reason == null) return;
  const r = await fetch(`${API}/compras/inventory/${variantId}`, {
    method: 'PATCH', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ delta, reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('Existencias ajustadas (+' + delta + ')', 'ok');
  loadComprasInventario();
}

async function physicalCount(variantId, expected) {
  if (typeof opsPrompt !== 'function') return;
  const counted = await opsPrompt({
    title: 'Conteo físico', message: `Existencia registrada: ${expected}. Indica las unidades contadas físicamente.`,
    label: 'Cantidad contada', inputType: 'number', min: 0, defaultValue: expected, confirmLabel: 'Continuar',
    validate: value => Number.isInteger(Number(value)) && Number(value) >= 0 ? null : 'Indica un entero igual o mayor a cero.',
  });
  if (counted == null) return;
  const reason = await opsPrompt({
    title: 'Confirmar conteo', message: `La diferencia será ${Number(counted) - Number(expected)} unidad(es).`,
    label: 'Observación o motivo', confirmLabel: 'Aplicar conteo',
    validate: value => value.trim().length >= 8 ? null : 'Escribe al menos 8 caracteres.',
  });
  if (reason == null) return;
  const r = await fetch(`${API}/compras/inventory/${variantId}/physical-count`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ counted: Number(counted), reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo aplicar el conteo.', 'danger'); return; }
  toast(data.message, 'ok'); loadComprasInventario();
}

async function editInventoryPolicy(variantId, currentMinimum, currentTarget) {
  if (typeof opsPrompt !== 'function') return;
  const minimum = await opsPrompt({
    title: 'Existencia mínima', message: 'Al alcanzar este nivel se recomendará reposición.',
    label: 'Mínimo', inputType: 'number', min: 0, defaultValue: currentMinimum, confirmLabel: 'Continuar',
    validate: value => Number.isInteger(Number(value)) && Number(value) >= 0 ? null : 'Indica un entero válido.',
  });
  if (minimum == null) return;
  const target = await opsPrompt({
    title: 'Objetivo de reposición', message: 'Cantidad deseada después de reponer.',
    label: 'Objetivo', inputType: 'number', min: Number(minimum), defaultValue: Math.max(currentTarget, Number(minimum)), confirmLabel: 'Guardar',
    validate: value => Number.isInteger(Number(value)) && Number(value) >= Number(minimum) ? null : `Debe ser al menos ${minimum}.`,
  });
  if (target == null) return;
  const r = await fetch(`${API}/compras/inventory/${variantId}/policy`, {
    method: 'PATCH', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ minimum: Number(minimum), target: Number(target) }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo guardar la política.', 'danger'); return; }
  toast(data.message, 'ok'); loadComprasInventario();
}

async function showInventoryKardex(variantId, sku) {
  const r = await fetch(`${API}/compras/inventory/${variantId}/kardex?limit=50`, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo cargar el kardex.', 'danger'); return; }
  const rows = data.movements || [];
  const labels = {
    purchase_receipt: 'Recepción de compra', sale_commitment: 'Reserva de venta',
    sale_release: 'Liberación de reserva', sale_fulfillment: 'Salida por venta',
    return_good: 'Devolución apta', return_damaged: 'Devolución dañada',
    physical_count: 'Conteo físico', adjustment: 'Ajuste', stock_set: 'Ajuste de stock',
  };
  const current = rows.length ? Number(rows[0].after || 0) : 0;
  const entries = rows.reduce((sum, row) => sum + Math.max(Number(row.quantity || 0), 0), 0);
  const exits = rows.reduce((sum, row) => sum + Math.abs(Math.min(Number(row.quantity || 0), 0)), 0);
  const table = rows.length ? `<div class="table-scroll"><table class="kardex-table"><thead><tr>
      <th>Fecha</th><th>Movimiento</th><th>Cantidad</th><th>Saldo</th><th>Referencia / motivo</th>
    </tr></thead><tbody>${rows.map(row => {
      const qty = Number(row.quantity || 0);
      const date = String(row.created_at || '').replace('T', ' ').slice(0, 16) || '—';
      const detail = [row.reference, row.reason].filter(Boolean).join(' · ');
      return `<tr><td>${comprasEsc(date)}</td><td>${comprasEsc(labels[row.movement_type] || row.movement_type || '—')}</td>
        <td class="${qty >= 0 ? 'kardex-qty--in' : 'kardex-qty--out'}">${qty > 0 ? '+' : ''}${qty}</td>
        <td>${Number(row.after || 0).toLocaleString('es-EC')}</td><td>${comprasEsc(detail || '—')}</td></tr>`;
    }).join('')}</tbody></table></div>` : '<p class="modal-sub">Todavía no existen movimientos registrados para esta variante.</p>';
  const html = `<div class="ops-confirm-content"><div class="kardex-summary">
      <div><small>Saldo actual</small><strong>${current.toLocaleString('es-EC')}</strong></div>
      <div><small>Entradas registradas</small><strong>+${entries.toLocaleString('es-EC')}</strong></div>
      <div><small>Salidas registradas</small><strong>-${exits.toLocaleString('es-EC')}</strong></div>
    </div>${table}</div>`;
  if (typeof opsNotice === 'function') await opsNotice({ title: `Kardex ${sku || '#' + variantId}`, html, wide: true });
  else if (typeof opsConfirm === 'function') await opsConfirm({ title: `Kardex ${sku || '#' + variantId}`, html, confirmLabel: 'Cerrar', wide: true });
}

async function loadComprasProveedores() {
  const body = document.getElementById('compras-vend-body');
  if (!body) return;
  await ensureVendorGeoMasters();
  renderVendorRegionTable();
  body.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
  const r = await fetch(API + '/compras/vendors', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Error al cargar', hint: data.message || 'Error al procesar' })
      : `<tr><td colspan="6">${data.message || 'Error al procesar'}</td></tr>`;
    return;
  }
  const rows = data.vendors || [];
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Sin proveedores', hint: 'Crea uno abajo o ejecuta Sincronizar catálogo (conserva proveedores existentes).' })
      : '<tr><td colspan="6">Sin proveedores.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(v => `
    <tr>
      <td>${v.vendor_id}</td>
      <td>${v.name}</td>
      <td>${v.email || '—'}</td>
      <td>${vendorGeoDisplay(v)}</td>
      <td>${v.active === false ? '<span class="badge badge--danger">Inactivo</span>' : '<span class="badge badge--ok">Activo</span>'}</td>
      <td>
        <button type="button" class="btn btn-ghost btn-ops"
          onclick='editVendor(${JSON.stringify({
            id: v.vendor_id,
            name: v.name,
            email: v.email || '',
            region_id: v.region_id || null,
            country_id: v.country_id || null,
            active: v.active !== false,
          })})'>Editar</button>
        <button type="button" class="btn btn-ghost btn-ops" onclick="toggleVendorStatus(${v.vendor_id}, ${v.active === false ? 'true' : 'false'})">
          ${v.active === false ? 'Habilitar' : 'Inhabilitar'}
        </button>
      </td>
    </tr>`).join('');
}

function editVendor(v) {
  const row = typeof v === 'object' ? v : { id: v };
  document.getElementById('vend-id').value = row.id || '';
  document.getElementById('vend-name').value = row.name || '';
  document.getElementById('vend-email').value = row.email || '';
  document.getElementById('vend-id').dataset.active = row.active === false ? 'false' : 'true';
  setVendorGeo(row.region_id, row.country_id);
  document.getElementById('vend-form-title').textContent = 'Editar proveedor #' + row.id;
}

function resetVendorForm() {
  document.getElementById('vend-id').value = '';
  document.getElementById('vend-name').value = '';
  document.getElementById('vend-email').value = '';
  document.getElementById('vend-id').dataset.active = 'true';
  setVendorGeo(null, null);
  document.getElementById('vend-form-title').textContent = 'Nuevo proveedor';
}

async function saveVendor() {
  const id = document.getElementById('vend-id').value;
  const body = {
    name: document.getElementById('vend-name').value.trim(),
    email: document.getElementById('vend-email').value.trim(),
    region_id: vendorGeoState.regionId,
    country_id: vendorGeoState.countryId,
    active: document.getElementById('vend-id').dataset.active !== 'false',
  };
  if (!body.name) { toast('Nombre obligatorio', 'warn'); return; }
  if (!body.country_id) { toast('Elige continente y país del proveedor', 'warn'); return; }
  const url = id ? `${API}/compras/vendors/${id}` : `${API}/compras/vendors`;
  const method = id ? 'PUT' : 'POST';
  const r = await fetch(url, {
    method, credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast(id ? 'Proveedor actualizado' : 'Proveedor creado', 'ok');
  resetVendorForm();
  loadComprasProveedores();
}

async function toggleVendorStatus(vendorId, active) {
  let reason = '';
  if (!active) {
    if (typeof opsPrompt !== 'function') { toast('No se pudo abrir el formulario.', 'danger'); return; }
    reason = await opsPrompt({
      title: 'Inhabilitar proveedor',
      message: 'El proveedor dejará de estar disponible para nuevas órdenes, pero conservará su historial.',
      label: 'Motivo',
      confirmLabel: 'Inhabilitar',
      validate: val => val.trim().length < 5 ? 'Escribe un motivo de al menos 5 caracteres.' : null,
    });
    if (reason == null) return;
  }
  const r = await fetch(`${API}/compras/vendors/${vendorId}/status`, {
    method: 'PATCH', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: !!active, reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo cambiar el estado.', 'danger'); return; }
  toast(data.message, 'ok');
  loadComprasProveedores();
}

function reqStatusBadge(st) {
  const map = {
    borrador: 'badge badge--warn',
    aprobada: 'badge badge--info',
    convertida: 'badge badge--ok',
    cancelada: 'badge badge--danger',
  };
  return `<span class="${map[st] || 'badge'}">${st || '—'}</span>`;
}

async function loadComprasRequisitions() {
  const body = document.getElementById('compras-preq-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="7">Cargando…</td></tr>';
  await fillPoVendorSelect();
  await fillPoVariantSelect();
  const vendSel = document.getElementById('preq-vendor');
  const varSel = document.getElementById('preq-variant');
  const poVend = document.getElementById('po-vendor');
  const poVar = document.getElementById('po-variant');
  if (vendSel && poVend) vendSel.innerHTML = poVend.innerHTML;
  if (varSel && poVar) varSel.innerHTML = poVar.innerHTML;
  const r = await fetch(`${API}/compras/requisitions?limit=40`, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(7, { title: 'Error al cargar', hint: data.message || 'Error' })
      : `<tr><td colspan="7">${data.message || 'Error'}</td></tr>`;
    return;
  }
  const rows = data.requisitions || [];
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(7, { title: 'Sin requisiciones', hint: 'Crea una requisición interna antes de generar la OC al proveedor.' })
      : '<tr><td colspan="7">Sin requisiciones</td></tr>';
    return;
  }
  body.innerHTML = rows.map(req => {
    const lines = (req.lines || []).map(l => `${l.sku || l.variant_id}×${l.quantity}`).join(', ');
    const st = req.status || '';
    const actions = [
      st === 'borrador' ? `<button type="button" class="btn btn-primary btn-ops" onclick="approveRequisition(${req.req_id})">Aprobar</button>` : '',
      st === 'aprobada' ? `<button type="button" class="btn btn-primary btn-ops" onclick="convertRequisition(${req.req_id})">Generar OC</button>` : '',
      !['convertida', 'cancelada'].includes(st) ? `<button type="button" class="btn btn-ghost btn-ops" onclick="cancelRequisition(${req.req_id})">Cancelar</button>` : '',
    ].filter(Boolean).join(' ') || '—';
    return `<tr>
      <td>${req.req_id}</td>
      <td>${req.vendor_name || req.vendor_id || '—'}</td>
      <td>${reqStatusBadge(st)}</td>
      <td>${lines || '—'}</td>
      <td>${req.created_at || '—'}</td>
      <td>${req.po_id ? `#${req.po_id}` : '—'}</td>
      <td style="white-space:nowrap">${actions}</td>
    </tr>`;
  }).join('');
}

async function createRequisition() {
  const vendorId = parseInt(document.getElementById('preq-vendor')?.value || '0', 10);
  const variantId = parseInt(document.getElementById('preq-variant')?.value || '0', 10);
  const qty = parseInt(document.getElementById('preq-qty')?.value || '0', 10);
  const cost = parseFloat(document.getElementById('preq-cost')?.value || '0');
  if (!vendorId || !variantId || qty < 1 || !Number.isFinite(cost) || cost <= 0) {
    toast('Proveedor, variante, cantidad y costo mayor a 0 son obligatorios.', 'warn');
    return;
  }
  const r = await fetch(`${API}/compras/requisitions`, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendor_id: vendorId, lines: [{ variant_id: variantId, quantity: qty, unit_cost: cost }] }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al crear requisición', 'danger'); return; }
  toast(data.message || 'Requisición creada', 'ok');
  loadComprasRequisitions();
}

async function approveRequisition(id) {
  const r = await fetch(`${API}/compras/requisitions/${id}/aprobar`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('Requisición aprobada', 'ok');
  loadComprasRequisitions();
}

async function convertRequisition(id) {
  const r = await fetch(`${API}/compras/requisitions/${id}/convertir-oc`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast(data.message || 'OC generada', 'ok');
  loadComprasRequisitions();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function cancelRequisition(id) {
  if (typeof opsConfirm === 'function') {
    const ok = await opsConfirm({ title: 'Cancelar requisición', message: `¿Cancelar requisición #${id}?`, confirmLabel: 'Cancelar', danger: true });
    if (!ok) return;
  }
  const r = await fetch(`${API}/compras/requisitions/${id}/cancelar`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('Requisición cancelada', 'ok');
  loadComprasRequisitions();
}

async function loadComprasOCs() {
  const body = document.getElementById('compras-po-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
  await fillPoVendorSelect();
  await fillPoVariantSelect();
  const r = await fetch(API + '/compras/purchase-orders?limit=40', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Error al cargar', hint: data.message || 'Error al procesar' })
      : `<tr><td colspan="6">${data.message || 'Error al procesar'}</td></tr>`;
    return;
  }
  const rows = data.orders || [];
  refreshComprasChips();
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Sin órdenes de compra', hint: 'Crea una OC en borrador arriba o desde Decisiones → Crear OC.' })
      : '<tr><td colspan="6">Sin órdenes de compra.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(po => {
    const lines = (po.lines || []).map(l => `${l.sku || l.variant_id} ${l.quantity_received}/${l.quantity_ordered}`).join(', ');
    const st = po.status || '';
    const canSend = st === 'borrador';
    const canRecv = st === 'enviada' || st === 'parcial';
    const canCancel = !['recibida', 'devuelta_parcial', 'devuelta', 'cancelada'].includes(st);
    const canReturn = ['recibida', 'devuelta_parcial'].includes(st);
    const linesAttr = encodeURIComponent(JSON.stringify(po.lines || []));
    const actions = [
      `<button type="button" class="btn btn-ghost btn-ops" onclick="openPoDetail(${po.po_id})">Ver</button>`,
      canSend ? `<button type="button" class="btn btn-primary btn-ops" onclick="sendPO(${po.po_id})">Enviar</button>` : '',
      canRecv ? `<button type="button" class="btn btn-primary btn-ops" onclick="receivePO(${po.po_id}, '${linesAttr}')">Recibir</button>` : '',
      canReturn ? `<button type="button" class="btn btn-ghost btn-ops" onclick="returnPO(${po.po_id}, '${linesAttr}')">Devolver</button>` : '',
      canCancel ? `<button type="button" class="btn btn-ghost btn-ops" onclick="cancelPO(${po.po_id})">Cancelar</button>` : '',
    ].filter(Boolean).join(' ') || '—';
    return `<tr>
      <td>${po.po_id}</td>
      <td>${po.vendor_name || po.vendor_id}</td>
      <td>${poStatusBadge(st)}</td>
      <td>${lines || '—'}</td>
      <td>${po.created_at || '—'}</td>
      <td style="white-space:nowrap">${actions}</td>
    </tr>`;
  }).join('');
}

async function fillPoVendorSelect() {
  const sel = document.getElementById('po-vendor');
  if (!sel) return;
  const r = await fetch(API + '/compras/vendors?active_only=1', { credentials: 'same-origin' });
  const data = await r.json();
  const prev = sel.value;
  sel.innerHTML = '<option value="">— Proveedor —</option>' +
    (data.vendors || []).map(v => `<option value="${v.vendor_id}" data-filter-region="${comprasEsc(regionLabel(v.region_name) || 'Sin región')}" data-filter-country="${comprasEsc(v.country || 'Sin país')}">${comprasEsc(v.name)}</option>`).join('');
  if (prev) sel.value = prev;
}

async function fillPoVariantSelect() {
  const sel = document.getElementById('po-variant');
  if (!sel) return;
  const r = await fetch(API + '/compras/inventory?limit=100', { credentials: 'same-origin' });
  const data = await r.json();
  const prev = sel.value;
  sel.innerHTML = '<option value="">— Variante / código —</option>' +
    (data.items || []).map(v => {
      const available = Number(v.available ?? v.inventory_quantity ?? 0);
      const minimum = Number(v.minimum_stock || 0);
      const stockGroup = available <= 0 ? 'Sin existencias' : available <= minimum ? 'Existencias bajas' : 'Disponible';
      return `<option value="${v.variant_id}" data-filter-category="${comprasEsc(v.category || 'Sin categoría')}" data-filter-vendor="${comprasEsc(v.vendor || 'Sin proveedor')}" data-filter-stock="${stockGroup}">${comprasEsc(v.sku || v.variant_id)} · ${comprasEsc(v.title)}</option>`;
    }).join('');
  if (prev) sel.value = prev;
}

async function createPO() {
  const vendor_id = parseInt(document.getElementById('po-vendor').value, 10);
  const variant_id = parseInt(document.getElementById('po-variant').value, 10);
  const quantity = parseInt(document.getElementById('po-qty').value, 10) || 0;
  const unit_cost = parseFloat(document.getElementById('po-cost').value) || 0;
  if (!vendor_id || !variant_id || quantity < 1 || !Number.isFinite(unit_cost) || unit_cost <= 0) {
    toast('Completa proveedor, variante, cantidad y un costo mayor a 0.', 'warn');
    return;
  }
  const r = await fetch(API + '/compras/purchase-orders', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendor_id, lines: [{ variant_id, quantity, unit_cost }] }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('OC #' + data.order.po_id + ' creada en borrador', 'ok');
  const hint = document.getElementById('po-prefill-hint');
  if (hint) hint.hidden = true;
  loadComprasOCs();
}

async function sendPO(id) {
  if (typeof opsConfirm !== 'function') {
    toast('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).', 'danger');
    return;
  }
  const ok = await opsConfirm({
    title: 'Enviar orden de compra',
    message: `¿Enviar OC #${id} al proveedor?`,
    confirmLabel: 'Enviar',
  });
  if (!ok) return;
  const r = await fetch(`${API}/compras/purchase-orders/${id}/send`, {
    method: 'POST', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast(data.message || 'OC enviada', 'ok');
  loadComprasOCs();
}

async function receivePO(id, linesRaw) {
  let lines = [];
  try {
    if (typeof linesRaw === 'string') {
      lines = JSON.parse(decodeURIComponent(linesRaw || '%5B%5D'));
    } else {
      lines = linesRaw || [];
    }
  } catch { lines = []; }
  const pending = lines.map(l => ({
    line_id: Number(l.line_id),
    pending: Number(l.quantity_ordered || 0) - Number(l.quantity_received || 0),
    label: l.sku || ('var ' + l.variant_id),
  })).filter(l => l.pending > 0);

  let receipts = null;
  if (pending.length === 1) {
    const p0 = pending[0];
    if (typeof opsPrompt !== 'function') {
      toast('No se pudo abrir el formulario. Recarga la página (Ctrl+F5).', 'danger');
      return;
    }
    const raw = await opsPrompt({
      title: 'Recibir mercancía',
      message: `Cantidad a recibir de ${p0.label} (máx. ${p0.pending}). Deja vacío para recibir todo el pendiente.`,
      label: 'Cantidad',
      defaultValue: String(p0.pending),
      inputType: 'number',
      confirmLabel: 'Recibir',
      validate: (val) => {
        if (val === '') return null;
        const qty = parseInt(val, 10);
        if (!Number.isFinite(qty) || qty < 1) return 'Indica un entero mayor a 0.';
        if (qty > p0.pending) return `Máximo ${p0.pending}.`;
        return null;
      },
    });
    if (raw === null) return;
    const qty = raw === '' ? p0.pending : parseInt(raw, 10);
    receipts = [{ line_id: p0.line_id, quantity: Math.min(qty, p0.pending) }];
  } else if (pending.length > 1) {
    let all = false;
    if (typeof opsConfirm === 'function') {
      all = await opsConfirm({
        title: 'Recibir mercancía',
        message: '¿Recibir TODO lo pendiente de todas las líneas? Cancelar te permitirá indicar cantidades por línea.',
        confirmLabel: 'Recibir todo',
      });
    }
    if (!all) {
      if (typeof opsPrompt !== 'function') {
        toast('No se pudo abrir el formulario. Recarga la página (Ctrl+F5).', 'danger');
        return;
      }
      receipts = [];
      for (const p of pending) {
        const raw = await opsPrompt({
          title: 'Recibir mercancía',
          message: `${p.label}: máximo ${p.pending}. Usa 0 para omitir esta línea.`,
          label: 'Cantidad',
          defaultValue: String(p.pending),
          inputType: 'number',
          confirmLabel: 'Aplicar',
          validate: (val) => {
            if (val === '') return 'Indica una cantidad (0 para omitir).';
            const qty = parseInt(val, 10);
            if (!Number.isFinite(qty) || qty < 0) return 'Cantidad inválida.';
            if (qty > p.pending) return `Máximo ${p.pending}.`;
            return null;
          },
        });
        if (raw === null) return;
        const qty = parseInt(raw, 10);
        if (qty > 0) receipts.push({ line_id: p.line_id, quantity: Math.min(qty, p.pending) });
      }
      if (!receipts.length) { toast('Nada que recibir', 'warn'); return; }
    }
  } else {
    if (typeof opsConfirm !== 'function') {
      toast('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).', 'danger');
      return;
    }
    const ok = await opsConfirm({
      title: 'Recibir mercancía',
      message: '¿Recibir cantidades pendientes y sumarlas al stock?',
      confirmLabel: 'Recibir',
    });
    if (!ok) return;
  }

  const r = await fetch(`${API}/compras/purchase-orders/${id}/receive`, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(receipts ? { receipts } : {}),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast(data.message || 'Mercancía recibida', 'ok');
  loadComprasOCs();
  if (comprasTab === 'inventario') loadComprasInventario();
}

async function cancelPO(id) {
  if (typeof opsConfirm !== 'function') {
    toast('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).', 'danger');
    return;
  }
  const ok = await opsConfirm({
    title: 'Cancelar orden de compra',
    message: `¿Cancelar OC #${id}?`,
    confirmLabel: 'Cancelar OC',
    danger: true,
  });
  if (!ok) return;
  const r = await fetch(`${API}/compras/purchase-orders/${id}/cancel`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('OC cancelada', 'ok');
  loadComprasOCs();
}

async function returnPO(id, linesRaw) {
  let lines = [];
  try { lines = JSON.parse(decodeURIComponent(linesRaw || '%5B%5D')); } catch { lines = []; }
  const available = lines.map(line => ({
    line_id: Number(line.line_id), label: line.sku || `Línea ${line.line_id}`,
    max: Math.max(Number(line.quantity_received || 0) - Number(line.quantity_returned || 0), 0),
  })).filter(line => line.max > 0);
  if (!available.length) { toast('Esta OC ya no tiene unidades disponibles para devolver.', 'warn'); return; }
  const reason = await opsPrompt({
    title: 'Devolver al proveedor', message: 'Explica el motivo. Se descontará del inventario y quedará en el kardex.',
    label: 'Motivo', confirmLabel: 'Continuar',
    validate: value => value.trim().length < 8 ? 'Escribe al menos 8 caracteres.' : null,
  });
  if (reason == null) return;
  const returns = [];
  for (const line of available) {
    const raw = await opsPrompt({
      title: `Devolver ${line.label}`, message: `Disponibles para devolver: ${line.max}. Usa 0 para omitir.`,
      label: 'Cantidad', inputType: 'number', min: 0, step: 1, defaultValue: '0', confirmLabel: 'Aplicar',
      validate: value => Number.isInteger(Number(value)) && Number(value) >= 0 && Number(value) <= line.max ? null : `Indica un entero entre 0 y ${line.max}.`,
    });
    if (raw == null) return;
    if (Number(raw) > 0) returns.push({ line_id: line.line_id, quantity: Number(raw) });
  }
  if (!returns.length) { toast('No se seleccionaron unidades para devolver.', 'warn'); return; }
  const r = await fetch(`${API}/compras/purchase-orders/${id}/return`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, returns }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { toast(data.message || 'No se pudo registrar la devolución.', 'danger'); return; }
  toast(data.message, 'ok'); loadComprasOCs();
}

window.returnPO = returnPO;

function cashMovementLabel(type) {
  const map = { payment_in: 'Entrada (pago)', refund_out: 'Salida (devolución)', adjustment: 'Ajuste' };
  return map[type] || type || '—';
}

function cashMovementBadge(type) {
  if (type === 'payment_in') return 'badge badge--ok';
  if (type === 'refund_out') return 'badge badge--danger';
  return 'badge';
}

async function loadComprasCaja() {
  const body = document.getElementById('compras-caja-body');
  const summaryEl = document.getElementById('compras-caja-summary');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const q = new URLSearchParams({ limit: 80 });
  const term = (document.getElementById('compras-caja-q')?.value || '').trim();
  const type = (document.getElementById('compras-caja-type')?.value || '').trim();
  if (term) q.set('q', term);
  if (type) q.set('type', type);
  const [r, accountingR, receivablesR, notesR, periodsR] = await Promise.all([
    fetch(`${API}/compras/cash-ledger?${q}`, { credentials: 'same-origin' }),
    fetch(`${API}/compras/accounting/summary`, { credentials: 'same-origin' }),
    fetch(`${API}/compras/accounting/receivables?limit=100`, { credentials: 'same-origin' }),
    fetch(`${API}/compras/accounting/credit-notes`, { credentials: 'same-origin' }),
    fetch(`${API}/compras/accounting/periods`, { credentials: 'same-origin' }),
  ]);
  const data = await r.json();
  const accounting = await accountingR.json();
  const receivables = await receivablesR.json();
  const notes = await notesR.json();
  const periods = await periodsR.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Error al cargar', hint: data.message || 'No se pudo cargar caja' })
      : `<tr><td colspan="8">${data.message || 'Error'}</td></tr>`;
    return;
  }
  const summary = data.summary || {};
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="ops-chips" style="margin-bottom:12px">
        <span class="ops-chip ops-chip--ok"><span>Entradas</span><strong>${fmtUSD(summary.total_in || 0)}</strong></span>
        <span class="ops-chip ops-chip--danger"><span>Salidas</span><strong>${fmtUSD(summary.total_out || 0)}</strong></span>
        <span class="ops-chip"><span>Neto</span><strong>${fmtUSD(summary.net || 0)}</strong></span>
        <span class="ops-chip"><span>Movimientos</span><strong>${summary.count || 0}</strong></span>
        <span class="ops-chip"><span>Por cobrar</span><strong>${fmtUSD(accounting.accounts_receivable || 0)}</strong></span>
        <span class="ops-chip"><span>Costos</span><strong>${fmtUSD(accounting.costs || 0)}</strong></span>
        <span class="ops-chip"><span>Utilidad bruta</span><strong>${fmtUSD(accounting.gross_profit || 0)}</strong></span>
        <span class="ops-chip"><span>IVA incluido</span><strong>${fmtUSD(accounting.tax_included || 0)}</strong></span>
      </div>`;
  }
  renderAccountingReceivables(receivables);
  loadAccountingMargins();
  renderAccountingCreditNotes(notes.credit_notes || []);
  const periodMeta = document.getElementById('accounting-period-meta');
  if (periodMeta) periodMeta.textContent = `${(periods.periods || []).length} período(s) cerrado(s)`;
  const rows = data.movements || [];
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Sin movimientos', hint: 'Los pagos y devoluciones registrados aparecerán aquí.' })
      : '<tr><td colspan="8">Sin movimientos</td></tr>';
    return;
  }
  body.innerHTML = rows.map(row => `
    <tr>
      <td style="font-family:var(--mono)">${row.movement_id}</td>
      <td>${(row.created_at || '').slice(0, 10) || '—'}</td>
      <td><span class="${cashMovementBadge(row.movement_type)}">${cashMovementLabel(row.movement_type)}</span></td>
      <td>${fmtUSD(row.amount)}</td>
      <td>#${row.request_id || '—'}</td>
      <td style="font-family:var(--mono)">${row.order_id || '—'}</td>
      <td>${row.reference || '—'}</td>
      <td>${row.payment_method || '—'}</td>
    </tr>`).join('');
}

function renderAccountingReceivables(data) {
  const body = document.getElementById('accounting-receivables-body');
  const meta = document.getElementById('accounting-receivables-meta');
  if (!body) return;
  const rows = data.receivables || [];
  const agingEl = document.getElementById('accounting-aging-summary');
  const aging = data.aging || {};
  if (agingEl) agingEl.innerHTML = [
    ['Por vencer','not_due'], ['1–30 días','1_30'], ['31–60 días','31_60'], ['61–90 días','61_90'], ['Más de 90','over_90'],
  ].map(([label,key]) => `<span class="ops-chip"><span>${label}</span><strong>${fmtUSD(aging[key]?.balance || 0)}</strong><small>${aging[key]?.count || 0} cuenta(s)</small></span>`).join('');
  if (meta) meta.textContent = `${rows.length} cuenta(s) · ${fmtUSD(data.total_due || 0)}`;
  body.innerHTML = rows.length ? rows.map(row => `
    <tr><td>#${row.request_id}</td><td>${row.client_name || row.client_email || '—'}</td>
    <td>${row.due_date || '—'}</td><td><span class="badge ${row.days_overdue > 30 ? 'badge--danger' : 'badge--warn'}">${row.days_overdue ? `${row.days_overdue} días` : 'Por vencer'}</span></td>
    <td>${fmtUSD(row.expected)}</td><td>${fmtUSD(row.net_paid)}</td><td><strong>${fmtUSD(row.balance_due)}</strong></td>
    <td><button type="button" class="btn btn-primary btn-sm" onclick="recordAccountingPayment(${row.request_id},${Number(row.balance_due)})">Abonar</button> <button type="button" class="btn btn-ghost btn-sm" onclick="showAccountingStatement('${encodeURIComponent(row.client_email || '').replace(/'/g,'%27')}')">Estado</button> <button type="button" class="btn btn-ghost btn-sm" onclick="showAccountingReconciliation(${row.request_id})">Conciliar</button></td></tr>`).join('')
    : (typeof opsEmptyRow === 'function' ? opsEmptyRow(8, { title: 'Cartera al día', hint: 'No hay saldos pendientes de cobro.' }) : '<tr><td colspan="8">No hay saldos pendientes.</td></tr>');
}

async function recordAccountingPayment(requestId, balance) {
  const amount = await opsPrompt({title:`Abono a solicitud #${requestId}`, message:`Saldo pendiente: ${fmtUSD(balance)}`, label:'Monto del abono', inputType:'number', min:0.01, step:0.01, confirmLabel:'Continuar', validate:v => Number(v)>0 && Number(v)<=balance ? null : 'El monto debe ser mayor a cero y no superar el saldo.'});
  if (amount == null) return;
  const reference = await opsPrompt({title:'Referencia del abono', message:'Utiliza una referencia única del comprobante.', label:'Referencia', confirmLabel:'Registrar abono', validate:v => v.trim().length>=6 ? null : 'Escribe al menos 6 caracteres.'});
  if (reference == null) return;
  const r = await fetch(`${API}/compras/accounting/receivables/${requestId}/payments`, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({amount:Number(amount), reference, payment_method:'tarjeta'})});
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo registrar el abono.', 'danger'); return; }
  toast(data.message || 'Abono registrado.', 'ok'); loadComprasCaja();
}

async function showAccountingStatement(encodedEmail) {
  const email = decodeURIComponent(encodedEmail || '');
  const r = await fetch(`${API}/compras/accounting/customers/${encodeURIComponent(email)}/statement`, {credentials:'same-origin'});
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo cargar el estado de cuenta.', 'danger'); return; }
  const t = data.totals || {};
  await opsConfirm({title:`Estado de cuenta · ${email}`, message:`${data.count || 0} operación(es) · Facturado: ${fmtUSD(t.charged)} · Pagado: ${fmtUSD(t.paid)} · Devuelto: ${fmtUSD(t.refunded)} · Saldo: ${fmtUSD(t.balance)}`, confirmLabel:'Cerrar'});
}

async function loadAccountingMargins() {
  const body = document.getElementById('accounting-margins-body'); if (!body) return;
  const group = document.getElementById('accounting-margin-group')?.value || 'product';
  const r = await fetch(`${API}/compras/accounting/margins?group_by=${encodeURIComponent(group)}&limit=100`, {credentials:'same-origin'});
  const data = await r.json();
  if (!r.ok) { body.innerHTML = `<tr><td colspan="7">${data.message || 'No se pudo cargar el margen.'}</td></tr>`; return; }
  body.innerHTML = (data.rows || []).length ? data.rows.map(row => `<tr><td><strong>${row.label}</strong></td><td>${row.orders}</td><td>${row.units}</td><td>${fmtUSD(row.revenue)}</td><td>${fmtUSD(row.cost)}</td><td>${fmtUSD(row.profit)}</td><td>${Number(row.margin_pct || 0).toFixed(2)}%</td></tr>`).join('') : (typeof opsEmptyRow === 'function' ? opsEmptyRow(7,{title:'Sin datos de margen',hint:'Los pedidos convertidos aparecerán aquí.'}) : '<tr><td colspan="7">Sin datos</td></tr>');
}

function renderAccountingCreditNotes(rows) {
  const body = document.getElementById('accounting-credit-notes-body');
  if (!body) return;
  body.innerHTML = rows.length ? rows.map(row => `
    <tr><td style="font-family:var(--mono)">${row.credit_note_number}</td><td>${(row.issued_at || '').slice(0, 10)}</td>
    <td>#${row.request_id}</td><td>${fmtUSD(row.amount)}</td><td>${row.reason || '—'}</td><td>${row.source === 'return' ? 'Devolución' : 'Manual'}</td></tr>`).join('')
    : (typeof opsEmptyRow === 'function' ? opsEmptyRow(6, { title: 'Sin notas de crédito', hint: 'Las devoluciones y ajustes autorizados aparecerán aquí.' }) : '<tr><td colspan="6">Sin notas de crédito.</td></tr>');
}

async function createManualCreditNote() {
  if (typeof opsPrompt !== 'function') { toast('No se pudo abrir el formulario.', 'danger'); return; }
  const requestRaw = await opsPrompt({
    title: 'Nueva nota de crédito', message: 'Indica la solicitud pagada que se ajustará.',
    label: 'Número de solicitud', inputType: 'number', min: 1, confirmLabel: 'Continuar',
    validate: value => Number.isInteger(Number(value)) && Number(value) > 0 ? null : 'Indica un número de solicitud válido.',
  });
  if (requestRaw == null) return;
  const amountRaw = await opsPrompt({
    title: `Nota para solicitud #${requestRaw}`, message: 'El monto no puede superar el valor pagado pendiente de devolución.',
    label: 'Monto', inputType: 'number', min: 0.01, step: 0.01, confirmLabel: 'Continuar',
    validate: value => Number(value) > 0 ? null : 'Indica un monto mayor a cero.',
  });
  if (amountRaw == null) return;
  const reason = await opsPrompt({
    title: 'Motivo del ajuste', message: 'Este dato quedará registrado en la trazabilidad contable.',
    label: 'Motivo', confirmLabel: 'Emitir nota',
    validate: value => value.trim().length >= 8 ? null : 'Escribe un motivo de al menos 8 caracteres.',
  });
  if (reason == null) return;
  const r = await fetch(`${API}/compras/accounting/credit-notes`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: Number(requestRaw), amount: Number(amountRaw), reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo emitir la nota de crédito.', 'danger'); return; }
  toast(data.message || 'Nota de crédito emitida.', 'ok');
  loadComprasCaja();
}

async function showAccountingReconciliation(requestId) {
  const r = await fetch(`${API}/compras/accounting/reconciliation/${requestId}`, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo conciliar.', 'danger'); return; }
  const text = `Esperado: ${fmtUSD(data.expected)} · Pagado: ${fmtUSD(data.paid)} · Reembolsado: ${fmtUSD(data.refunded)} · Facturado: ${fmtUSD(data.invoiced)} · Saldo: ${fmtUSD(data.balance_due)}`;
  if (typeof opsConfirm === 'function') await opsConfirm({ title: `Conciliación #${requestId}`, message: text, confirmLabel: 'Cerrar' });
}

async function closeAccountingPeriod(kind) {
  if (typeof opsPrompt !== 'function') { toast('No se pudo abrir el formulario.', 'danger'); return; }
  const today = new Date().toISOString().slice(0, 10);
  const value = kind === 'monthly' ? today.slice(0, 7) : today;
  const reason = await opsPrompt({
    title: kind === 'monthly' ? `Cerrar mes ${value}` : `Cerrar día ${value}`,
    message: 'Después del cierre no se podrán registrar pagos, reembolsos ni notas de crédito en ese período.',
    label: 'Motivo del cierre', confirmLabel: 'Cerrar período',
    validate: val => val.trim().length < 8 ? 'Escribe un motivo de al menos 8 caracteres.' : null,
  });
  if (reason == null) return;
  const r = await fetch(`${API}/compras/accounting/periods/close`, {
    method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ period_type: kind, value, reason }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo cerrar el período.', 'danger'); return; }
  toast(data.message, 'ok'); loadComprasCaja();
}

async function loadComprasMerma() {
  const body = document.getElementById('compras-merma-body');
  const meta = document.getElementById('compras-merma-meta');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const q = new URLSearchParams({ limit: 80 });
  const term = (document.getElementById('compras-merma-q')?.value || '').trim();
  if (term) q.set('q', term);
  const r = await fetch(`${API}/compras/scrap?${q}`, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Error al cargar', hint: data.message || 'No se pudo cargar merma' })
      : `<tr><td colspan="8">${data.message || 'Error'}</td></tr>`;
    return;
  }
  const items = data.items || [];
  if (meta) meta.textContent = `${data.total_records || items.length} registro(s) · ${data.total_units || 0} unidad(es)`;
  if (!items.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Sin merma registrada', hint: 'Las devoluciones con productos dañados aparecerán aquí.' })
      : '<tr><td colspan="8">Sin registros</td></tr>';
    return;
  }
  body.innerHTML = items.map(row => `
    <tr>
      <td>${row.created_at || '—'}</td>
      <td>#${row.request_id || '—'}</td>
      <td>${row.product_name || '—'}</td>
      <td style="font-family:var(--mono)">${row.sku || '—'}</td>
      <td>${row.variant_id || '—'}</td>
      <td>${row.quantity || 0}</td>
      <td>${row.reason || '—'}</td>
      <td>${row.reviewed_by || '—'}</td>
    </tr>`).join('');
}

async function openPoDetail(poId) {
  const modal = document.getElementById('po-detail-modal');
  const body = document.getElementById('po-detail-body');
  const title = document.getElementById('po-detail-title');
  if (!modal || !body) return;
  modal.hidden = false;
  if (title) title.textContent = `OC a proveedor #${poId}`;
  body.innerHTML = '<p class="modal-sub">Cargando…</p>';
  try {
    const [poR, histR] = await Promise.all([
      fetch(`${API}/compras/purchase-orders/${poId}`, { credentials: 'same-origin' }),
      fetch(`${API}/compras/purchase-orders/${poId}/historial`, { credentials: 'same-origin' }),
    ]);
    const poData = await poR.json();
    const histData = await histR.json();
    if (!poR.ok) {
      body.innerHTML = `<p class="modal-sub">${poData.message || 'No se pudo cargar la OC'}</p>`;
      return;
    }
    const po = poData.order || poData;
    const lineRows = (po.lines || []).map(l => `<tr>
      <td>${l.sku || l.variant_id}</td><td>${l.quantity_ordered}</td><td>${l.quantity_received}</td><td>${l.quantity_returned || 0}</td><td>${fmtUSD(l.unit_cost)}</td>
    </tr>`).join('');
    body.innerHTML = `
      <div class="detail-grid">
        <div><span class="detail-label">Proveedor</span><strong>${po.vendor_name || po.vendor?.name || '—'}</strong></div>
        <div><span class="detail-label">Estado</span>${poStatusBadge(po.status)}</div>
        <div><span class="detail-label">Creada</span>${po.created_at || '—'}</div>
        ${po.received_at ? `<div><span class="detail-label">Recibida</span>${po.received_at}</div>` : ''}
      </div>
      <table class="detail-table" style="margin-top:10px"><thead><tr><th>SKU / Var.</th><th>Pedido</th><th>Recibido</th><th>Devuelto</th><th>Costo</th></tr></thead>
      <tbody>${lineRows || '<tr><td colspan="5">Sin líneas</td></tr>'}</tbody></table>
      ${typeof renderAuditTrail === 'function' ? renderAuditTrail(histData.entries || [], { title: 'Historial de la OC' }) : ''}`;
  } catch {
    body.innerHTML = '<p class="modal-sub">Error de red al cargar la OC.</p>';
  }
}

function closePoDetail() {
  const modal = document.getElementById('po-detail-modal');
  if (modal) modal.hidden = true;
}

window.openPoDetail = openPoDetail;
window.closePoDetail = closePoDetail;

window.selectVendorRegion = selectVendorRegion;
window.selectVendorCountry = selectVendorCountry;
window.loadComprasPage = loadComprasPage;
window.showComprasTab = showComprasTab;
window.loadComprasCaja = loadComprasCaja;
window.loadComprasMerma = loadComprasMerma;
window.loadComprasRequisitions = loadComprasRequisitions;
window.createRequisition = createRequisition;
window.approveRequisition = approveRequisition;
window.convertRequisition = convertRequisition;
window.cancelRequisition = cancelRequisition;
window.quickPOFromStock = quickPOFromStock;
window.applyComprasPoPrefill = applyComprasPoPrefill;
window.openComprasPo = function openComprasPo(poId) {
  window._comprasPrefill = { tab: 'ocs' };
  const nav = document.querySelector('.nav-item[data-page="compras"]');
  if (typeof showPage === 'function') showPage('compras', nav);
  else loadComprasPage();
  if (poId) toast('OC #' + poId + ' — revisa el listado abajo', 'info');
};
