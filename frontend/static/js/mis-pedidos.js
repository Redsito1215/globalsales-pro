/* Mis pedidos — cliente B2B */
async function loadMisPedidosPage() {
  const body = document.getElementById('mis-pedidos-body');
  const meta = document.getElementById('mis-pedidos-meta');
  const chips = document.getElementById('mis-pedidos-chips');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(7, {
          title: 'Inicia sesión',
          hint: 'Accede con tu cuenta para ver el seguimiento de tus pedidos.',
        })
      : '<tr><td colspan="7">Inicia sesión para ver tus pedidos.</td></tr>';
    if (chips) chips.innerHTML = '';
    return;
  }
  body.innerHTML = '<tr><td colspan="7">Cargando…</td></tr>';
  const r = await fetch(API + '/solicitudes/mias?limit=50', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="7">${data.message || 'Error al cargar'}</td></tr>`;
    return;
  }
  const rows = data.requests || [];
  if (meta) meta.textContent = `${data.total || 0} pedido${(data.total || 0) === 1 ? '' : 's'}`;
  if (chips) {
    const counts = { pending_pay: 0, open: 0, delivered: 0 };
    rows.forEach(req => {
      const pay = req.payment_status || 'pendiente_pago';
      if (pay === 'pendiente_pago' && !['rechazada', 'cancelada', 'devuelta'].includes(req.status)) counts.pending_pay++;
      if (['pendiente', 'en_revision', 'aprobada', 'convertida', 'enviada'].includes(req.status)) counts.open++;
      if (req.status === 'entregada') counts.delivered++;
    });
    chips.innerHTML = `
      <span class="ops-chip"><span>Total</span><strong>${data.total || rows.length}</strong></span>
      <span class="ops-chip ops-chip--warn"><span>Por pagar</span><strong>${counts.pending_pay}</strong></span>
      <span class="ops-chip"><span>En curso</span><strong>${counts.open}</strong></span>
      <span class="ops-chip ops-chip--muted"><span>Entregados</span><strong>${counts.delivered}</strong></span>`;
  }
  if (!rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(7, {
          title: 'Aún no tienes pedidos',
          hint: 'Explora el catálogo B2B y envía tu primera solicitud.',
          ctaLabel: 'Ir a Vitrina',
          ctaOnclick: "showPage('tienda')",
        })
      : '<tr><td colspan="7">Aún no tienes pedidos. Compra en la Vitrina B2B.</td></tr>';
    return;
  }
  const noMap = {};
  [...rows]
    .sort((a, b) => Number(a.request_id || 0) - Number(b.request_id || 0))
    .forEach((r, i) => { noMap[r.request_id] = i + 1; });
  body.innerHTML = rows.map(req => {
    const lines = (req.lines || []).map(l => `${l.product_name || l.product_id} ×${l.quantity}`).join(', ');
    const label = typeof solicitudStatusLabel === 'function' ? solicitudStatusLabel(req.status) : req.status;
    const cls = typeof solicitudStatusClass === 'function' ? solicitudStatusClass(req.status) : 'badge';
    const pay = req.payment_status || 'pendiente_pago';
    const payHtml = typeof paymentBadge === 'function' ? paymentBadge(pay) : pay;
    const canCancel = ['pendiente', 'en_revision'].includes(req.status);
    const canPay = pay === 'pendiente_pago' && !['rechazada', 'cancelada', 'devuelta'].includes(req.status);
    const n = Number(req.client_order_no) || noMap[req.request_id] || 0;
    const pedidoLabel = n ? `Pedido ${n}` : 'Pedido';
    const actions = `
      <button type="button" class="btn btn-ghost btn-ops" onclick="openSolicitudDetail(${req.request_id})">Detalle</button>
      <button type="button" class="btn btn-ghost btn-ops" onclick="openSolicitudPdf(${req.request_id})">PDF</button>
      ${canPay ? `<button type="button" class="btn btn-primary btn-ops" onclick="openPagoModal(${req.request_id})">Pagar</button>` : ''}
      ${canCancel ? `<button type="button" class="btn btn-ghost btn-ops" onclick="cancelarMiSolicitud(${req.request_id})">Cancelar</button>` : ''}`;
    const track = req.tracking_number
      ? `<span class="table-sub">GT</span> <code>${req.tracking_number}</code>`
      : '—';
    const orderRef = req.order_id ? `<div class="table-sub">Venta ${req.order_id}</div>` : '';
    return `<tr>
      <td><strong>${pedidoLabel}</strong>${orderRef}</td>
      <td>${lines}</td>
      <td><span class="${cls}">${label}</span></td>
      <td>${payHtml}</td>
      <td>${req.created_at || '—'}</td>
      <td>${track}</td>
      <td style="white-space:nowrap">${actions}</td>
    </tr>`;
  }).join('');
}

function openPagoModal(requestId) {
  const modal = document.getElementById('pago-modal');
  const hid = document.getElementById('pago-request-id');
  if (!modal || !hid) return;
  hid.value = String(requestId);
  modal.hidden = false;
}

function closePagoModal() {
  const modal = document.getElementById('pago-modal');
  if (modal) modal.hidden = true;
}

async function confirmClientePagar() {
  const id = parseInt(document.getElementById('pago-request-id')?.value || '0', 10);
  const method = document.getElementById('pago-method')?.value || 'transferencia';
  if (!id) return;
  const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
  let r;
  try {
    r = await fetch(`${base}/solicitudes/${id}/pagar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method }),
    });
  } catch (e) {
    if (typeof opsToast === 'function') opsToast('Error de red al pagar. ¿Está el servidor en marcha?', 'danger');
    else alert('Error de red al pagar. ¿Está el servidor en marcha?');
    return;
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = data.message || (`No se pudo registrar el pago (${r.status}). Reinicia la web e intenta de nuevo.`);
    if (typeof opsToast === 'function') opsToast(msg, 'danger');
    else alert(msg);
    return;
  }
  closePagoModal();
  if (typeof opsToast === 'function') opsToast('Pago registrado. El vendedor podrá convertir y enviar.', 'ok');
  else alert('Pago registrado. El vendedor podrá convertir y enviar el pedido.');
  loadMisPedidosPage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function cancelarMiSolicitud(id) {
  if (!confirm('¿Cancelar esta solicitud?')) return;
  const r = await fetch(`${API}/solicitudes/${id}/cancelar`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  loadMisPedidosPage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}
