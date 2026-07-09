/* Q3 — CRUD pedidos (admin) */
async function loadPedidosAdmin() {
  const body = document.getElementById('pedidos-admin-body');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = '<tr><td colspan="6">Inicia sesión para administrar pedidos.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
  const r = await fetch(API + '/sales/orders?limit=30', { credentials: 'same-origin' });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    body.innerHTML = `<tr><td colspan="6">${data.message || 'Error al cargar pedidos'}</td></tr>`;
    return;
  }
  const rows = await r.json();
  if (!Array.isArray(rows) || !rows.length) {
    body.innerHTML = '<tr><td colspan="6">Sin pedidos</td></tr>';
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
      <td>${admin ? `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="deletePedido('${row.order_id}')">Eliminar</button>` : '—'}</td>
    </tr>`).join('');
}

async function createPedidoAdmin() {
  if (window._authUser?.role !== 'administrador') { alert('Solo administradores.'); return; }
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
  if (!r.ok) { alert(data.message || 'Error'); return; }
  alert('Pedido creado: ' + data.order.order_id);
  await loadPedidosAdmin();
}

async function deletePedido(orderId) {
  if (!confirm('¿Eliminar pedido ' + orderId + '?')) return;
  const r = await fetch(API + '/sales/orders/' + encodeURIComponent(orderId), {
    method: 'DELETE', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  await loadPedidosAdmin();
}

function showVentasTab(tab) {
  document.querySelectorAll('.ventas-tab-panel').forEach(p => p.hidden = true);
  document.querySelectorAll('.ventas-tab-btn').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('ventas-panel-' + tab);
  const btn = document.querySelector('.ventas-tab-btn[data-tab="' + tab + '"]');
  if (panel) panel.hidden = false;
  if (btn) btn.classList.add('active');
  if (tab === 'solicitudes') loadSolicitudes();
  if (tab === 'pedidos') { loadPedidosAdmin(); loadSolicitudes(); }
}
