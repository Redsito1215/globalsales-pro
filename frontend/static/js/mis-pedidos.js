/* Mis pedidos — cliente B2B */
const pagoModalState = { requestId: null, staff: false, offline: false };

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
      const offline = typeof isOfflineRequest === 'function' && isOfflineRequest(req);
      const needsPay = pay === 'pendiente_pago' || (pay === 'credito' && !offline);
      if (needsPay && !['rechazada', 'cancelada', 'devuelta'].includes(req.status)) counts.pending_pay++;
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
    const offline = typeof isOfflineRequest === 'function' && isOfflineRequest(req);
    const canPay = (pay === 'pendiente_pago' || (pay === 'credito' && !offline))
      && !['rechazada', 'cancelada', 'devuelta'].includes(req.status);
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

async function openPagoModal(requestId, opts) {
  const o = opts || {};
  const modal = document.getElementById('pago-modal');
  const hid = document.getElementById('pago-request-id');
  const modeEl = document.getElementById('pago-mode');
  const lead = document.getElementById('pago-modal-lead');
  const methodSel = document.getElementById('pago-method');
  if (!modal || !hid) return;

  let offline = false;
  try {
    const r = await fetch(`${API}/solicitudes/${requestId}`, { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (r.ok && data.request) {
      offline = typeof isOfflineRequest === 'function' && isOfflineRequest(data.request);
    }
  } catch (_) { /* ignore */ }

  pagoModalState.requestId = requestId;
  pagoModalState.staff = !!o.staff;
  pagoModalState.offline = offline;
  hid.value = String(requestId);
  if (modeEl) modeEl.value = o.staff ? 'staff' : 'client';
  if (typeof fillPaymentMethodSelect === 'function') {
    fillPaymentMethodSelect(methodSel, offline);
  }
  if (lead) {
    lead.textContent = o.staff
      ? (offline
        ? 'Registra el pago presencial. Solo aplica cuando el cliente no tiene cuenta o el pedido es offline.'
        : 'Registra el pago porque el correo del pedido no tiene cuenta en la plataforma.')
      : (offline
        ? 'Simulación de pago presencial. Elige tarjeta o efectivo y tarjeta bancaria.'
        : 'Simulación de pago online. Elige tarjeta, crédito o cuenta bancaria.');
  }
  const title = document.getElementById('pago-modal-title');
  if (title) title.textContent = o.staff ? 'Registrar pago (vendedor)' : 'Pagar solicitud';
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
}

function closePagoModal() {
  const modal = document.getElementById('pago-modal');
  if (modal) {
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
  }
  pagoModalState.requestId = null;
  pagoModalState.staff = false;
}

async function confirmClientePagar() {
  const id = parseInt(document.getElementById('pago-request-id')?.value || '0', 10);
  const method = document.getElementById('pago-method')?.value || 'tarjeta';
  const staff = pagoModalState.staff || document.getElementById('pago-mode')?.value === 'staff';
  if (!id) return;
  const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
  const url = staff ? `${base}/solicitudes/${id}/registrar-pago` : `${base}/solicitudes/${id}/pagar`;
  let r;
  try {
    r = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method }),
    });
  } catch (e) {
    notifyErr('Error de red al pagar. ¿Está el servidor en marcha?');
    return;
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = data.message || (`No se pudo registrar el pago (${r.status}). Reinicia la web e intenta de nuevo.`);
    notifyErr(msg);
    return;
  }
  closePagoModal();
  const offline = pagoModalState.offline
    || String(data.request?.channel_name || '').trim().toLowerCase() === 'offline'
    || Number(data.request?.channel_id) === 2;
  if (staff) {
    notifyOk('Pago registrado por el vendedor.');
    if (typeof loadSolicitudes === 'function') loadSolicitudes();
  } else {
    notifyOk(offline
      ? 'Pago registrado. El vendedor podrá convertir la venta presencial.'
      : 'Pago registrado. El vendedor podrá convertir y enviar.');
    loadMisPedidosPage();
  }
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function cancelarMiSolicitud(id) {
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Cancelar solicitud',
    message: '¿Cancelar esta solicitud? Esta acción no se puede deshacer.',
    confirmLabel: 'Cancelar pedido',
    danger: true,
  });
  if (!ok) return;
  const r = await fetch(`${API}/solicitudes/${id}/cancelar`, { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error'); return; }
  notifyOk('Solicitud cancelada.');
  loadMisPedidosPage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

window.openPagoModal = openPagoModal;
window.closePagoModal = closePagoModal;
window.confirmClientePagar = confirmClientePagar;
