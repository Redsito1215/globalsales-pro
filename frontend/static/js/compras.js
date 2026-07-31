/* Q4 Compras — proveedores, inventario, OCs */
let comprasTab = 'inventario';

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
  if (typeof opsToast === 'function') opsToast(msg, type || 'info');
  else alert(msg);
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
  body.innerHTML = '<tr><td colspan="7">Cargando…</td></tr>';
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
      ? opsEmptyRow(7, { title: 'Error', hint: data.message || 'No se pudo cargar inventario' })
      : `<tr><td colspan="7">${data.message || 'Error'}</td></tr>`;
    return;
  }
  const rows = data.items || [];
  refreshComprasChips();
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(7, {
          title: 'Sin SKUs',
          hint: 'Ejecuta Sync catálogo en Maestros para generar variantes e inventario.',
          ctaLabel: 'Ir a Maestros',
          ctaOnclick: "showPage('datos')",
        })
      : '<tr><td colspan="7">Sin SKUs. Ejecuta Sync catálogo en Maestros.</td></tr>';
    return;
  }
  const thr = parseInt(document.getElementById('compras-inv-thr')?.value || '20', 10);
  body.innerHTML = rows.map(row => {
    const qty = Number(row.inventory_quantity || 0);
    const sug = Math.max(thr - qty, 10);
    const lowBadge = qty <= thr ? '<span class="badge badge--danger">Bajo</span>' : '<span class="badge badge--ok">OK</span>';
    return `<tr>
      <td>${row.variant_id}</td>
      <td>${row.title}<br><span class="table-sub">${row.sku || ''}</span></td>
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
      <td>${v.country || '—'}</td>
      <td>${v.active === false ? '<span class="badge badge--danger">Inactivo</span>' : '<span class="badge badge--ok">Activo</span>'}</td>
      <td>
        <button type="button" class="btn btn-ghost btn-ops"
          onclick='editVendor(${v.vendor_id}, ${JSON.stringify(v.name)}, ${JSON.stringify(v.email || "")}, ${JSON.stringify(v.country || "")})'>Editar</button>
      </td>
    </tr>`).join('');
}

function editVendor(id, name, email, country) {
  document.getElementById('vend-id').value = id;
  document.getElementById('vend-name').value = name || '';
  document.getElementById('vend-email').value = email || '';
  document.getElementById('vend-country').value = country || '';
  document.getElementById('vend-form-title').textContent = 'Editar proveedor #' + id;
}

function resetVendorForm() {
  document.getElementById('vend-id').value = '';
  document.getElementById('vend-name').value = '';
  document.getElementById('vend-email').value = '';
  document.getElementById('vend-country').value = '';
  document.getElementById('vend-form-title').textContent = 'Nuevo proveedor';
}

async function saveVendor() {
  const id = document.getElementById('vend-id').value;
  const body = {
    name: document.getElementById('vend-name').value.trim(),
    email: document.getElementById('vend-email').value.trim(),
    country: document.getElementById('vend-country').value.trim(),
    active: true,
  };
  if (!body.name) { toast('Nombre obligatorio', 'warn'); return; }
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
  if (!confirm('¿Enviar OC #' + id + ' al proveedor?')) return;
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
    const raw = prompt(
      `Cantidad a recibir de ${pending[0].label} (máx ${pending[0].pending}).\nVacío o Cancelar en el siguiente paso: vacío = todo.`,
      String(pending[0].pending)
    );
    if (raw === null) return;
    const qty = raw.trim() === '' ? pending[0].pending : parseInt(raw, 10);
    if (!Number.isFinite(qty) || qty < 1) { toast('Cantidad inválida', 'warn'); return; }
    receipts = [{ line_id: pending[0].line_id, quantity: Math.min(qty, pending[0].pending) }];
  } else if (pending.length > 1) {
    const all = confirm('¿Recibir TODO lo pendiente de todas las líneas?\n\nAceptar = todo · Cancelar = indicar cantidades por línea.');
    if (!all) {
      receipts = [];
      for (const p of pending) {
        const raw = prompt(`Recibir ${p.label} (máx ${p.pending}). 0 para omitir.`, String(p.pending));
        if (raw === null) return;
        const qty = parseInt(raw, 10);
        if (!Number.isFinite(qty) || qty < 0) { toast('Cantidad inválida', 'warn'); return; }
        if (qty > 0) receipts.push({ line_id: p.line_id, quantity: Math.min(qty, p.pending) });
      }
      if (!receipts.length) { toast('Nada que recibir', 'warn'); return; }
    }
  } else if (!confirm('¿Recibir cantidades pendientes y sumarlas al stock?')) {
    return;
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
  if (!confirm('¿Cancelar OC #' + id + '?')) return;
  const r = await fetch(`${API}/compras/purchase-orders/${id}/cancel`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error', 'danger'); return; }
  toast('OC cancelada', 'ok');
  loadComprasOCs();
}

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
