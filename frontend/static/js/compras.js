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
  if (tab === 'ocs') loadComprasOCs();
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
    <span class="ops-chip ${low ? 'ops-chip--danger' : ''}"><span>Stock bajo</span><strong>${low}</strong></span>
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
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
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
      ? opsEmptyRow(8, { title: 'Error', hint: data.message || 'No se pudo cargar inventario' })
      : `<tr><td colspan="8">${data.message || 'Error'}</td></tr>`;
    return;
  }
  renderWarehouseBanner(data.warehouse);
  const rows = data.items || [];
  refreshComprasChips();
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, {
          title: 'Sin SKUs',
          hint: 'Ejecuta Sync catálogo en Maestros para generar variantes e inventario.',
          ctaLabel: 'Ir a Maestros',
          ctaOnclick: "showPage('datos')",
        })
      : '<tr><td colspan="8">Sin SKUs. Ejecuta Sync catálogo en Maestros.</td></tr>';
    return;
  }
  const whName = (data.warehouse && data.warehouse.name) || 'Bodega General';
  const thr = parseInt(document.getElementById('compras-inv-thr')?.value || '20', 10);
  body.innerHTML = rows.map(row => {
    const qty = Number(row.inventory_quantity || 0);
    const sug = Math.max(thr - qty, 10);
    const lowBadge = qty <= thr ? '<span class="badge badge--danger">Bajo</span>' : '<span class="badge badge--ok">OK</span>';
    return `<tr>
      <td>${row.variant_id}</td>
      <td>${row.title}<br><span class="table-sub">${row.sku || ''}</span></td>
      <td><span class="badge badge--info">${row.warehouse || whName}</span></td>
      <td>${row.vendor}</td>
      <td><strong>${qty}</strong> ${lowBadge}</td>
      <td>$${Number(row.price || 0).toFixed(2)}</td>
      <td>$${Number(row.cost || 0).toFixed(2)}</td>
      <td style="white-space:nowrap">
        <input type="number" id="inv-set-${row.variant_id}" value="${qty}" style="width:70px" />
        <button type="button" class="btn btn-ghost btn-ops" onclick="saveStock(${row.variant_id})">Guardar</button>
        <button type="button" class="btn btn-ghost btn-ops" onclick="bumpStock(${row.variant_id},10)">+10</button>
        <button type="button" class="btn btn-primary btn-ops" onclick="quickPOFromStock(${row.variant_id},${row.vendor_id || 0},${Number(row.cost || 0)},${sug})">OC</button>
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
  const r = await fetch(`${API}/compras/inventory/${variantId}`, {
    method: 'PATCH', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ available: val }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('Stock actualizado', 'ok');
  loadComprasInventario();
}

async function bumpStock(variantId, delta) {
  const r = await fetch(`${API}/compras/inventory/${variantId}`, {
    method: 'PATCH', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ delta }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('Stock ajustado (+' + delta + ')', 'ok');
  loadComprasInventario();
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
      ? opsEmptyRow(6, { title: 'Error', hint: data.message || 'Error' })
      : `<tr><td colspan="6">${data.message || 'Error'}</td></tr>`;
    return;
  }
  const rows = data.vendors || [];
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Sin proveedores', hint: 'Crea uno abajo o ejecuta Sync catálogo (conserva proveedores existentes).' })
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
          })})'>Editar</button>
      </td>
    </tr>`).join('');
}

function editVendor(v) {
  const row = typeof v === 'object' ? v : { id: v };
  document.getElementById('vend-id').value = row.id || '';
  document.getElementById('vend-name').value = row.name || '';
  document.getElementById('vend-email').value = row.email || '';
  setVendorGeo(row.region_id, row.country_id);
  document.getElementById('vend-form-title').textContent = 'Editar proveedor #' + row.id;
}

function resetVendorForm() {
  document.getElementById('vend-id').value = '';
  document.getElementById('vend-name').value = '';
  document.getElementById('vend-email').value = '';
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
    active: true,
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
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast(id ? 'Proveedor actualizado' : 'Proveedor creado', 'ok');
  resetVendorForm();
  loadComprasProveedores();
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
      ? opsEmptyRow(6, { title: 'Error', hint: data.message || 'Error' })
      : `<tr><td colspan="6">${data.message || 'Error'}</td></tr>`;
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
    const canCancel = !['recibida', 'cancelada'].includes(st);
    const linesAttr = encodeURIComponent(JSON.stringify(po.lines || []));
    const actions = [
      canSend ? `<button type="button" class="btn btn-primary btn-ops" onclick="sendPO(${po.po_id})">Enviar</button>` : '',
      canRecv ? `<button type="button" class="btn btn-primary btn-ops" onclick="receivePO(${po.po_id}, '${linesAttr}')">Recibir</button>` : '',
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
    (data.vendors || []).map(v => `<option value="${v.vendor_id}">${v.name}</option>`).join('');
  if (prev) sel.value = prev;
}

async function fillPoVariantSelect() {
  const sel = document.getElementById('po-variant');
  if (!sel) return;
  const r = await fetch(API + '/compras/inventory?limit=100', { credentials: 'same-origin' });
  const data = await r.json();
  const prev = sel.value;
  sel.innerHTML = '<option value="">— Variante / SKU —</option>' +
    (data.items || []).map(v => `<option value="${v.variant_id}">${v.sku || v.variant_id} · ${v.title}</option>`).join('');
  if (prev) sel.value = prev;
}

async function createPO() {
  const vendor_id = parseInt(document.getElementById('po-vendor').value, 10);
  const variant_id = parseInt(document.getElementById('po-variant').value, 10);
  const quantity = parseInt(document.getElementById('po-qty').value, 10) || 0;
  const unit_cost = parseFloat(document.getElementById('po-cost').value) || 0;
  if (!vendor_id || !variant_id || quantity < 1) {
    toast('Completa proveedor, variante y cantidad', 'warn');
    return;
  }
  const r = await fetch(API + '/compras/purchase-orders', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendor_id, lines: [{ variant_id, quantity, unit_cost }] }),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
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
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
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
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
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
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('OC cancelada', 'ok');
  loadComprasOCs();
}

window.selectVendorRegion = selectVendorRegion;
window.selectVendorCountry = selectVendorCountry;
window.loadComprasPage = loadComprasPage;
window.showComprasTab = showComprasTab;
window.quickPOFromStock = quickPOFromStock;
window.applyComprasPoPrefill = applyComprasPoPrefill;
window.openComprasPo = function openComprasPo(poId) {
  window._comprasPrefill = { tab: 'ocs' };
  const nav = document.querySelector('.nav-item[data-page="compras"]');
  if (typeof showPage === 'function') showPage('compras', nav);
  else loadComprasPage();
  if (poId) toast('OC #' + poId + ' — revisa el listado abajo', 'info');
};
