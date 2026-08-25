/* Q3 — CRUD pedidos históricos (admin) */
function toast(msg, type) {
  notify(msg, type || 'info');
}

async function loadPedidosAdmin() {
  const body = document.getElementById('pedidos-admin-body');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Sesión requerida', hint: 'Inicia sesión para administrar pedidos históricos.' })
      : '<tr><td colspan="6">Inicia sesión para administrar pedidos.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
  const r = await fetch(API + '/sales/orders?limit=30', { credentials: 'same-origin' });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Error al cargar', hint: data.message || 'Error al cargar pedidos' })
      : `<tr><td colspan="6">${data.message || 'Error al cargar pedidos'}</td></tr>`;
    return;
  }
  const rows = await r.json();
  if (!Array.isArray(rows) || !rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(6, { title: 'Sin pedidos históricos', hint: 'Los pedidos convertidos desde solicitudes aparecen aquí.' })
      : '<tr><td colspan="6">Sin pedidos</td></tr>';
    return;
  }
  const admin = window._authUser?.role === 'administrador';
  body.innerHTML = rows.map(row => `
    <tr>
      <td style="font-family:var(--mono)">${row.order_id}</td>
      <td>${row.country}</td>
      <td>${row.item_type}</td>
      <td>${row.units_sold}</td>
      <td>${fmtUSD(row.total_revenue)}</td>
      <td>${admin
        ? `<button type="button" class="btn btn-ghost btn-ops" onclick="openPedidoEditModal('${row.order_id}')">Editar</button>
           <button type="button" class="btn btn-ghost btn-ops" onclick="deletePedido('${row.order_id}')">Eliminar</button>`
        : '—'}</td>
    </tr>`).join('');
}

async function openPedidoEditModal(orderId) {
  if (window._authUser?.role !== 'administrador') { toast('Solo administradores.', 'warn'); return; }
  const modal = document.getElementById('pedido-edit-modal');
  if (!modal) return;
  const r = await fetch(API + '/sales/orders/' + encodeURIComponent(orderId), { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'No se pudo cargar el pedido', 'danger'); return; }
  const line = (data.lines && data.lines[0]) || data.order || data;
  document.getElementById('ep-order-id').value = orderId;
  document.getElementById('ep-region').value = line.region || '';
  document.getElementById('ep-country').value = line.country || '';
  document.getElementById('ep-item').value = line.item_type || '';
  document.getElementById('ep-channel').value = line.sales_channel || '';
  document.getElementById('ep-priority').value = line.order_priority || 'M';
  document.getElementById('ep-units').value = line.units_sold ?? '';
  document.getElementById('ep-price').value = line.unit_price ?? '';
  document.getElementById('ep-cost').value = line.unit_cost ?? '';
  modal.hidden = false;
}

function closePedidoEditModal() {
  const modal = document.getElementById('pedido-edit-modal');
  if (modal) modal.hidden = true;
}

async function savePedidoEdit() {
  if (window._authUser?.role !== 'administrador') { toast('Solo administradores.', 'warn'); return; }
  const orderId = document.getElementById('ep-order-id').value;
  const body = {
    region: document.getElementById('ep-region').value.trim(),
    country: document.getElementById('ep-country').value.trim(),
    item_type: document.getElementById('ep-item').value.trim(),
    sales_channel: document.getElementById('ep-channel').value.trim(),
    order_priority: document.getElementById('ep-priority').value.trim() || 'M',
    units_sold: parseInt(document.getElementById('ep-units').value, 10) || 0,
    unit_price: parseFloat(document.getElementById('ep-price').value) || 0,
    unit_cost: parseFloat(document.getElementById('ep-cost').value) || 0,
  };
  const r = await fetch(API + '/sales/orders/' + encodeURIComponent(orderId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al guardar', 'danger'); return; }
  toast('Pedido actualizado', 'ok');
  closePedidoEditModal();
  await loadPedidosAdmin();
  if (typeof refreshAnalyticsLagBanners === 'function') refreshAnalyticsLagBanners();
}

async function createPedidoAdmin() {
  if (window._authUser?.role !== 'administrador') { toast('Solo administradores.', 'warn'); return; }
  const body = {
    region: document.getElementById('np-region').value.trim(),
    country: document.getElementById('np-country').value.trim(),
    item_type: document.getElementById('np-item').value.trim(),
    sales_channel: document.getElementById('np-channel').value.trim(),
    order_priority: document.getElementById('np-priority').value.trim() || 'M',
    units_sold: parseInt(document.getElementById('np-units').value, 10) || 1,
    unit_price: parseFloat(document.getElementById('np-price').value) || 0,
    unit_cost: parseFloat(document.getElementById('np-cost').value) || 0,
  };
  const r = await fetch(API + '/sales/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('Pedido creado: ' + data.order.order_id, 'ok');
  await loadPedidosAdmin();
}

async function deletePedido(orderId) {
  if (typeof opsConfirm !== 'function') {
    toast('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).', 'danger');
    return;
  }
  const ok = await opsConfirm({
    title: 'Eliminar pedido',
    message: `¿Eliminar pedido ${orderId}?`,
    confirmLabel: 'Eliminar',
    danger: true,
  });
  if (!ok) return;
  const r = await fetch(API + '/sales/orders/' + encodeURIComponent(orderId), {
    method: 'DELETE', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { toast(data.message || 'Error al procesar', 'danger'); return; }
  toast('Pedido eliminado', 'ok');
  await loadPedidosAdmin();
}

function showVentasTab(tab) {
  if (tab === 'pedidos' && !hasPermission('orders.read')) {
    toast('No tienes permiso para explorar pedidos históricos.', 'warn');
    tab = 'solicitudes';
  }
  document.querySelectorAll('.ventas-tab-panel').forEach(p => p.hidden = true);
  document.querySelectorAll('.ventas-tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('ventas-panel-' + tab);
  const btn = document.querySelector('.ventas-tab-btn[data-tab="' + tab + '"]');
  if (panel) panel.hidden = false;
  if (btn) btn.classList.add('active');
  const createBox = document.getElementById('pedidos-create-box');
  if (createBox) createBox.hidden = window._authUser?.role !== 'administrador';
  if (tab === 'solicitudes') {
    loadSolicitudes();
    if (typeof refreshAnalyticsLagBanners === 'function') refreshAnalyticsLagBanners();
  }
  if (tab === 'pedidos') loadPedidosAdmin();
}

window.openPedidoEditModal = openPedidoEditModal;
window.closePedidoEditModal = closePedidoEditModal;
window.savePedidoEdit = savePedidoEdit;
