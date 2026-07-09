/* Q3 Ventas — solicitudes de compra */
let solicitudesState = { requests: [], total: 0 };

const SOLICITUD_STATUS_LABELS = {
  pendiente: 'Pendiente',
  en_revision: 'En revisión',
  aprobada: 'Aprobada',
  convertida: 'Convertida',
  rechazada: 'Rechazada',
  cancelada: 'Cancelada',
};
window.SOLICITUD_STATUS_LABELS = SOLICITUD_STATUS_LABELS;

function canConvertWithoutApproval() {
  return window._authUser?.role === 'administrador';
}

function solicitudStatusClass(status) {
  if (status === 'convertida') return 'badge badge--ok';
  if (status === 'rechazada' || status === 'cancelada') return 'badge badge--danger';
  if (status === 'aprobada') return 'badge badge--info';
  if (status === 'en_revision') return 'badge badge--warn';
  return 'badge';
}

function solicitudStatusLabel(status) {
  return SOLICITUD_STATUS_LABELS[status] || status || '—';
}

function solicitudDetailBtn(id) {
  return `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="openSolicitudDetail(${id})">Ver</button>`;
}

function solicitudActions(req) {
  if (!hasPermission('ventas.manage')) return solicitudDetailBtn(req.request_id);
  const status = req.status;
  const detail = solicitudDetailBtn(req.request_id);
  if (status === 'convertida') {
    return `${detail} <span style="font-size:10px;color:var(--muted)">Procesada · ${req.order_id || '—'}</span>`;
  }
  if (status === 'rechazada' || status === 'cancelada') {
    return `${detail} <span style="font-size:10px;color:var(--muted)">Cerrada</span>`;
  }
  if (status === 'aprobada') {
    return `${detail}
      <button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="convertirSolicitud(${req.request_id})">Convertir venta</button>`;
  }
  const rejectBtn = `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="setSolicitudEstado(${req.request_id},'rechazada')">Rechazar</button>`;
  const reviewBtn = status === 'pendiente'
    ? `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="setSolicitudEstado(${req.request_id},'en_revision')">Revisar</button>`
    : '';
  const approveBtn = `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="setSolicitudEstado(${req.request_id},'aprobada')">Aprobar</button>`;
  const convertBtn = canConvertWithoutApproval()
    ? `<button type="button" class="btn btn-ghost" style="font-size:10px;padding:4px 6px" onclick="convertirSolicitud(${req.request_id})">Convertir venta</button>`
    : `<span style="font-size:10px;color:var(--muted)">Aprueba antes de convertir</span>`;
  return `${detail} ${reviewBtn} ${approveBtn} ${convertBtn} ${rejectBtn}`;
}

async function loadVentasPage() {
  await loadSolicitudes();
  await loadVentasMastersForForm();
}

async function loadSolicitudes() {
  const body = document.getElementById('solicitudes-body');
  const meta = document.getElementById('solicitudes-meta');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = '<tr><td colspan="7">Inicia sesión para ver solicitudes.</td></tr>';
    return;
  }
  if (!hasPermission('ventas.manage')) {
    body.innerHTML = '<tr><td colspan="7">No tienes permiso para gestionar solicitudes comerciales.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="7">Cargando…</td></tr>';
  const status = document.getElementById('sol-filter-status')?.value ?? 'activas';
  const q = new URLSearchParams({ limit: 50, offset: 0 });
  if (status) q.set('status', status);
  const r = await fetch(API + '/solicitudes?' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="7">${data.message || 'Error'}</td></tr>`;
    return;
  }
  solicitudesState.requests = data.requests || [];
  solicitudesState.total = data.total || 0;
  if (meta) {
    meta.textContent = status === 'activas'
      ? `${data.total || 0} pendientes de gestión`
      : `${data.total || 0} solicitudes`;
  }
  if (!solicitudesState.requests.length) {
    const emptyMsg = status === 'activas'
      ? 'No hay solicitudes pendientes de gestión.'
      : 'Sin solicitudes con este filtro.';
    body.innerHTML = `<tr><td colspan="7">${emptyMsg}</td></tr>`;
    return;
  }
  body.innerHTML = solicitudesState.requests.map(req => {
    const lines = (req.lines || []).map(l => `${l.product_name || l.product_id} ×${l.quantity}`).join(', ');
    return `<tr>
      <td>${req.request_id}</td>
      <td>${req.client_name}<br><span style="font-size:10px;color:var(--muted)">${req.client_email}</span></td>
      <td>${lines}</td>
      <td><span class="${solicitudStatusClass(req.status)}">${solicitudStatusLabel(req.status)}</span></td>
      <td>${req.created_at || '—'}</td>
      <td>${req.order_id || '—'}</td>
      <td>${solicitudActions(req)}</td>
    </tr>`;
  }).join('');
}

async function setSolicitudEstado(id, status) {
  const r = await fetch(`${API}/solicitudes/${id}/estado`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ status }),
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  await loadSolicitudes();
}

async function convertirSolicitud(id) {
  if (!confirm('¿Convertir esta solicitud en venta(s) en sales_records?')) return;
  const r = await fetch(`${API}/solicitudes/${id}/convertir`, {
    method: 'POST', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  alert(`Venta creada. Order ID: ${data.order_id}`);
  await loadSolicitudes();
}

async function loadVentasMastersForForm() {
  /* reservado para selects en formularios futuros */
}
