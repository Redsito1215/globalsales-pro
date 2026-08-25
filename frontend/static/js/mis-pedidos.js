/* Mis pedidos — cliente B2B */
const pagoModalState = { requestId: null, staff: false, offline: false, total: 0, idempotencyKey: null };

function paymentAttemptKey() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `pay-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function safePagoCardMetadata() {
  const digits = String(document.getElementById('pago-card-number')?.value || '').replace(/\D/g, '');
  const exp = String(document.getElementById('pago-card-exp')?.value || '').split('/');
  return {
    brand: typeof detectPagoCardBrand === 'function' ? detectPagoCardBrand(digits) : 'TARJETA',
    last4: digits.slice(-4), exp_month: Number(exp[0]), exp_year: 2000 + Number(exp[1]),
  };
}

function formatPagoMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '$0.00';
  return `$${n.toFixed(2)}`;
}

function bindPagoCardInputs() {
  const form = document.getElementById('pago-card-form');
  const number = document.getElementById('pago-card-number');
  const exp = document.getElementById('pago-card-exp');
  const cvv = document.getElementById('pago-card-cvv');
  const name = document.getElementById('pago-card-name');

  const touchPreview = () => {
    if (typeof updatePagoCardPreview === 'function') updatePagoCardPreview();
    if (typeof clearPagoFieldErrors === 'function') clearPagoFieldErrors();
  };

  if (number && !number.dataset.bound) {
    number.dataset.bound = '1';
    number.addEventListener('input', () => {
      number.value = typeof formatPagoCardNumber === 'function'
        ? formatPagoCardNumber(number.value)
        : number.value;
      touchPreview();
    });
  }
  if (exp && !exp.dataset.bound) {
    exp.dataset.bound = '1';
    exp.addEventListener('input', () => {
      exp.value = typeof formatPagoCardExpiry === 'function'
        ? formatPagoCardExpiry(exp.value)
        : exp.value;
      touchPreview();
    });
    exp.addEventListener('blur', () => {
      if (typeof validatePagoCardExpiryField === 'function') validatePagoCardExpiryField();
    });
  }
  if (cvv && !cvv.dataset.bound) {
    cvv.dataset.bound = '1';
    cvv.addEventListener('input', () => {
      cvv.value = String(cvv.value || '').replace(/\D/g, '').slice(0, 4);
      touchPreview();
    });
  }
  if (name && !name.dataset.bound) {
    name.dataset.bound = '1';
    name.addEventListener('input', touchPreview);
  }
  if (form && !form.dataset.bound) {
    form.dataset.bound = '1';
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      confirmClientePagar();
    });
  }
}

function setPagoSummary(requestId, total) {
  const ref = document.getElementById('pago-order-ref');
  const totalEl = document.getElementById('pago-total');
  if (ref) ref.textContent = `#${requestId}`;
  if (totalEl) totalEl.textContent = formatPagoMoney(total);
}

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
      const needsPay = pay === 'pendiente_pago'
        && req.status === 'aprobada'
        && !['rechazada', 'cancelada', 'devuelta'].includes(req.status);
      if (needsPay) counts.pending_pay++;
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
          hint: 'Explora el catálogo y envía tu primera solicitud.',
          ctaLabel: 'Ir a la tienda',
          ctaOnclick: "showPage('tienda')",
        })
      : '<tr><td colspan="7">Aún no tienes pedidos. Compra en la tienda.</td></tr>';
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
    const canPay = typeof canClientPayRequest === 'function'
      ? canClientPayRequest(req)
      : (pay === 'pendiente_pago' && req.status === 'aprobada');
    const n = Number(req.client_order_no) || noMap[req.request_id] || 0;
    const pedidoLabel = n ? `Pedido ${n}` : 'Pedido';
    const actions = `
      <button type="button" class="btn btn-ghost btn-ops" onclick="openSolicitudDetail(${req.request_id})">Detalle</button>
      <button type="button" class="btn btn-ghost btn-ops" onclick="openSolicitudPdf(${req.request_id})">PDF</button>
      ${canPay ? `<button type="button" class="btn btn-primary btn-ops" onclick="openPagoModal(${req.request_id})">Pagar con tarjeta</button>` : ''}
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
  if (!modal || !hid) return;

  let offline = false;
  let total = 0;
  try {
    const r = await fetch(`${API}/solicitudes/${requestId}`, { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (r.ok && data.request) {
      const req = data.request;
      if (!o.staff && typeof canClientPayRequest === 'function' && !canClientPayRequest(req)) {
        notifyErr(req.status === 'aprobada'
          ? 'Este pedido no admite pago en este momento.'
          : 'Tu pedido debe estar aprobado antes de pagar.');
        return;
      }
      if (o.staff && req.status !== 'aprobada') {
        notifyErr('Aprueba la solicitud antes de registrar el pago.');
        return;
      }
      offline = typeof isOfflineRequest === 'function' && isOfflineRequest(req);
      total = Number(req.total != null ? req.total : req.subtotal || 0);
      pagoModalState.total = total;
    }
  } catch (_) { /* ignore */ }

  pagoModalState.requestId = requestId;
  pagoModalState.staff = !!o.staff;
  pagoModalState.offline = offline;
  pagoModalState.idempotencyKey = paymentAttemptKey();
  hid.value = String(requestId);
  if (modeEl) modeEl.value = o.staff ? 'staff' : 'client';
  if (typeof resetPagoCardForm === 'function') resetPagoCardForm();
  if (!o.staff && window._authUser?.role === 'cliente') {
    const nameEl = document.getElementById('pago-card-name');
    const defaultName = String(window._authUser.name || '').trim();
    if (nameEl && defaultName) {
      nameEl.value = defaultName;
      if (typeof updatePagoCardPreview === 'function') updatePagoCardPreview();
    }
  }
  bindPagoCardInputs();
  setPagoSummary(requestId, total);
  if (lead) {
    lead.textContent = o.staff
      ? (offline
        ? 'Ingresa los datos de la tarjeta del cliente para registrar el cobro presencial.'
        : 'Ingresa los datos de la tarjeta para registrar el pago del cliente.')
      : 'Completa los datos de la tarjeta. Verás una vista previa antes de confirmar.';
  }
  const title = document.getElementById('pago-modal-title');
  if (title) title.textContent = o.staff ? 'Registrar pago con tarjeta' : 'Pagar con tarjeta';
  const confirmBtn = document.getElementById('pago-confirm-btn');
  if (confirmBtn) {
    confirmBtn.textContent = o.staff ? 'Registrar pago' : `Pagar ${formatPagoMoney(total)}`;
    confirmBtn.disabled = false;
  }
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.getElementById('pago-card-name')?.focus();
}

function closePagoModal() {
  const modal = document.getElementById('pago-modal');
  if (modal) {
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
  }
  if (typeof resetPagoCardForm === 'function') resetPagoCardForm();
  pagoModalState.requestId = null;
  pagoModalState.staff = false;
  pagoModalState.total = 0;
  pagoModalState.idempotencyKey = null;
}

async function confirmClientePagar() {
  const id = parseInt(document.getElementById('pago-request-id')?.value || '0', 10);
  const staff = pagoModalState.staff || document.getElementById('pago-mode')?.value === 'staff';
  const confirmBtn = document.getElementById('pago-confirm-btn');
  if (!id) return;
  const validationMsg = typeof validatePagoCardForm === 'function' ? validatePagoCardForm() : '';
  if (validationMsg) {
    notifyWarn('Completa correctamente los datos de la tarjeta.');
    return;
  }
  if (confirmBtn) confirmBtn.disabled = true;
  const card = safePagoCardMetadata();
  const idempotencyKey = pagoModalState.idempotencyKey || paymentAttemptKey();
  pagoModalState.idempotencyKey = idempotencyKey;
  try {
    if (typeof simulatePagoCardCharge === 'function') {
      try {
        await simulatePagoCardCharge();
      } catch (chargeErr) {
        const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
        const message = String(chargeErr.message || 'Pago rechazado').toLowerCase();
        const outcome = message.includes('fondos') ? 'insufficient_funds' : 'declined';
        fetch(`${base}/solicitudes/${id}/intentos-pago`, {
          method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outcome, failure_code: outcome, idempotency_key: idempotencyKey, card }),
        }).catch(() => {});
        if (confirmBtn) confirmBtn.disabled = false;
        notifyErr(chargeErr.message || 'El pago fue rechazado.');
        return;
      }
    }
    const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
    const url = staff ? `${base}/solicitudes/${id}/registrar-pago` : `${base}/solicitudes/${id}/pagar`;
    const r = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method: 'tarjeta', idempotency_key: idempotencyKey, card }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (typeof setPagoProcessing === 'function') setPagoProcessing(false);
      if (confirmBtn) confirmBtn.disabled = false;
      const code = data.code || '';
      const msg = data.message || (`No se pudo registrar el pago (${r.status}). Reinicia la web e intenta de nuevo.`);
      if (code === 'already_paid') {
        notifyWarn(msg || 'Esta solicitud ya está pagada.');
      } else {
        notifyErr(msg);
      }
      return;
    }
    if (typeof setPagoProcessing === 'function') {
      setPagoProcessing(true, 'Pago aprobado ✓');
      await new Promise((resolve) => setTimeout(resolve, 500));
      setPagoProcessing(false);
    }
    closePagoModal();
    const offline = pagoModalState.offline
      || String(data.request?.channel_name || '').trim().toLowerCase() === 'offline'
      || Number(data.request?.channel_id) === 2;
    if (staff) {
      notifyOk('Pago con tarjeta registrado por el vendedor.');
      if (typeof loadSolicitudes === 'function') loadSolicitudes();
    } else {
      notifyOk(offline
        ? 'Pago con tarjeta registrado correctamente. El vendedor podrá convertir la venta presencial.'
        : 'Pago con tarjeta registrado correctamente. El vendedor podrá convertir y enviar.');
      loadMisPedidosPage();
    }
    if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
  } catch (e) {
    if (typeof setPagoProcessing === 'function') setPagoProcessing(false);
    if (confirmBtn) confirmBtn.disabled = false;
    notifyErr('Error de red al pagar. ¿Está el servidor en marcha?');
  }
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
  if (!r.ok) { notifyErr(data.message || 'Error al procesar'); return; }
  notifyOk('Solicitud cancelada.');
  loadMisPedidosPage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

window.openPagoModal = openPagoModal;
window.closePagoModal = closePagoModal;
window.confirmClientePagar = confirmClientePagar;

document.addEventListener('DOMContentLoaded', () => {
  bindPagoCardInputs();
  const confirmBtn = document.getElementById('pago-confirm-btn');
  if (confirmBtn) confirmBtn.addEventListener('click', confirmClientePagar);
});
