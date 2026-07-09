/* Mis pedidos — cliente B2B */
async function loadMisPedidosPage() {
  const body = document.getElementById('mis-pedidos-body');
  const meta = document.getElementById('mis-pedidos-meta');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = '<tr><td colspan="6">Inicia sesión para ver tus pedidos.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="6">Cargando…</td></tr>';
  const r = await fetch(API + '/solicitudes/mias?limit=50', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="6">${data.message || 'Error al cargar'}</td></tr>`;
    return;
  }
  const rows = data.requests || [];
  if (meta) meta.textContent = `${data.total || 0} solicitudes`;
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6">Aún no tienes pedidos. Compra en la Vitrina B2B.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(req => {
    const lines = (req.lines || []).map(l => `${l.product_name || l.product_id} ×${l.quantity}`).join(', ');
    const label = typeof solicitudStatusLabel === 'function' ? solicitudStatusLabel(req.status) : req.status;
    const cls = typeof solicitudStatusClass === 'function' ? solicitudStatusClass(req.status) : 'badge';
    const canCancel = ['pendiente', 'en_revision'].includes(req.status);
    const actions = `
      <button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="openSolicitudDetail(${req.request_id})">Detalle</button>
      <button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="openSolicitudPdf(${req.request_id})">PDF</button>
      ${canCancel ? `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="cancelarMiSolicitud(${req.request_id})">Cancelar</button>` : ''}`;
    return `<tr>
      <td>${req.request_id}</td>
      <td>${lines}</td>
      <td><span class="${cls}">${label}</span></td>
      <td>${req.created_at || '—'}</td>
      <td>${req.order_id || '—'}</td>
      <td>${actions}</td>
    </tr>`;
  }).join('');
}

async function cancelarMiSolicitud(id) {
  if (!confirm('¿Cancelar esta solicitud?')) return;
  const r = await fetch(`${API}/solicitudes/${id}/cancelar`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  loadMisPedidosPage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}
