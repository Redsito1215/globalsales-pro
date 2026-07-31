/* Q3 Ventas — solicitudes de compra */
let solicitudesState = { requests: [], total: 0 };

const SOLICITUD_STATUS_LABELS = {
  pendiente: 'Pendiente',
  en_revision: 'En revisión',
  aprobada: 'Aprobada',
  convertida: 'Convertida',
  enviada: 'Enviada',
  entregada: 'Entregada',
  devuelta: 'Devuelta',
  rechazada: 'Rechazada',
  cancelada: 'Cancelada',
};
window.SOLICITUD_STATUS_LABELS = SOLICITUD_STATUS_LABELS;

const PAYMENT_LABELS = {
  pendiente_pago: 'Pendiente pago',
  pagado: 'Pagado',
  credito: 'Crédito',
};

function paymentLabel(s) {
  return PAYMENT_LABELS[s] || s || 'Pendiente pago';
}

function paymentBadge(s) {
  const st = s || 'pendiente_pago';
  if (st === 'pagado') return `<span class="badge badge--ok">${paymentLabel(st)}</span>`;
  if (st === 'credito') return `<span class="badge badge--info">${paymentLabel(st)}</span>`;
  return `<span class="badge badge--warn">${paymentLabel(st)}</span>`;
}

function canConvertWithoutApproval() {
  return hasPermission('ventas.convert_bypass');
}

function solicitudStatusClass(status) {
  if (status === 'convertida' || status === 'enviada' || status === 'entregada') return 'badge badge--ok';
  if (status === 'devuelta') return 'badge badge--warn';
  if (status === 'rechazada' || status === 'cancelada') return 'badge badge--danger';
  if (status === 'aprobada') return 'badge badge--info';
  if (status === 'en_revision') return 'badge badge--warn';
  return 'badge';
}

function solicitudStatusLabel(status) {
  return SOLICITUD_STATUS_LABELS[status] || status || '—';
}

function solicitudDetailBtn(id) {
  return `<button type="button" class="btn btn-ghost btn-ops" onclick="openSolicitudDetail(${id})">Ver</button>`;
}

function payButtons(req) {
  if (!hasPermission('ventas.manage')) return '';
  if (['rechazada', 'cancelada'].includes(req.status)) return '';
  const pay = req.payment_status || 'pendiente_pago';
  if (pay === 'pagado') return '';
  if (pay === 'credito') {
    return `<span style="font-size:10px;color:var(--muted)">Crédito · espera envío</span>`;
  }
  return `
    <span style="font-size:10px;color:var(--muted)">Espera pago del cliente</span>
    <button type="button" class="btn btn-ghost btn-ops" onclick="setSolicitudPago(${req.request_id},'credito')">Crédito</button>`;
}

function solicitudActions(req) {
  if (!hasPermission('ventas.manage')) return solicitudDetailBtn(req.request_id);
  const status = req.status;
  const detail = solicitudDetailBtn(req.request_id);
  const pay = payButtons(req);
  if (status === 'entregada') {
    return `${detail} ${pay}
      <button type="button" class="btn btn-primary btn-ops" onclick="devolverSolicitud(${req.request_id})">Devolver</button>
      <span style="font-size:10px;color:var(--muted)">${req.tracking_number || req.order_id || '—'}</span>`;
  }
  if (status === 'devuelta') {
    const restock = req.return_restock_units != null ? req.return_restock_units : '—';
    const damaged = req.return_damaged_units != null ? req.return_damaged_units : '—';
    const cond = req.return_condition || '—';
    return `${detail} <span style="font-size:10px;color:var(--muted)">Devuelta (${cond}) · apto ${restock} · dañado ${damaged}</span>`;
  }
  if (status === 'enviada') {
    return `${detail} ${pay}
      <button type="button" class="btn btn-primary btn-ops" onclick="setSolicitudEstado(${req.request_id},'entregada')">Marcar entregada</button>`;
  }
  if (status === 'convertida') {
    const payOk = ['pagado', 'credito'].includes(req.payment_status);
    return `${detail} ${pay}
      ${payOk
        ? `<button type="button" class="btn btn-primary btn-ops" onclick="setSolicitudEstado(${req.request_id},'enviada')">Marcar enviada</button>`
        : `<span style="font-size:10px;color:var(--muted)">Espera pago del cliente o usa crédito</span>`}
      <span style="font-size:10px;color:var(--muted)">${req.order_id || ''}</span>`;
  }
  if (status === 'rechazada' || status === 'cancelada') {
    return `${detail} <span style="font-size:10px;color:var(--muted)">Cerrada</span>`;
  }
  if (status === 'aprobada') {
    const payOk = ['pagado', 'credito'].includes(req.payment_status);
    return `${detail} ${pay}
      ${payOk
        ? `<button type="button" class="btn btn-primary btn-ops" onclick="convertirSolicitud(${req.request_id})">Convertir venta</button>`
        : `<span style="font-size:10px;color:var(--muted)">Espera pago del cliente para convertir</span>`}`;
  }
  const rejectBtn = `<button type="button" class="btn btn-ghost btn-ops" onclick="setSolicitudEstado(${req.request_id},'rechazada')">Rechazar</button>`;
  const reviewBtn = status === 'pendiente'
    ? `<button type="button" class="btn btn-ghost btn-ops" onclick="setSolicitudEstado(${req.request_id},'en_revision')">Revisar</button>`
    : '';
  const approveBtn = `<button type="button" class="btn btn-primary btn-ops" onclick="setSolicitudEstado(${req.request_id},'aprobada')">Aprobar</button>`;
  const payOk = ['pagado', 'credito'].includes(req.payment_status);
  let convertBtn = `<span style="font-size:10px;color:var(--muted)">Aprueba antes de convertir</span>`;
  if (canConvertWithoutApproval()) {
    convertBtn = payOk
      ? `<button type="button" class="btn btn-primary btn-ops" onclick="convertirSolicitud(${req.request_id})">Convertir venta</button>`
      : `<span style="font-size:10px;color:var(--muted)">Espera pago del cliente para convertir</span>`;
  }
  return `${detail} ${pay} ${reviewBtn} ${approveBtn} ${convertBtn} ${rejectBtn}`;
}

async function loadVentasPage() {
  await loadSolicitudes();
  await refreshVentasBadge();
  const pedidosTab = document.querySelector('.ventas-tab-btn[data-tab="pedidos"]');
  const createBox = document.getElementById('pedidos-create-box');
  if (createBox) createBox.hidden = window._authUser?.role !== 'administrador';
  if (pedidosTab && !hasPermission('orders.read')) {
    pedidosTab.hidden = true;
  } else if (pedidosTab) {
    pedidosTab.hidden = false;
  }
}

async function refreshVentasBadge() {
  const badge = document.getElementById('ventas-nav-badge');
  if (!badge) return;
  if (!window._authUser || !hasPermission('ventas.manage')) {
    badge.hidden = true;
    return;
  }
  try {
    const r = await fetch(API + '/solicitudes/pendientes/count', { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) return;
    const n = data.pending || 0;
    badge.textContent = n > 99 ? '99+' : String(n);
    badge.hidden = n <= 0;
  } catch { /* ignore */ }
}

async function loadSolicitudes() {
  const body = document.getElementById('solicitudes-body');
  const meta = document.getElementById('solicitudes-meta');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Inicia sesión', hint: 'Accede para gestionar solicitudes comerciales.' })
      : '<tr><td colspan="8">Inicia sesión para ver solicitudes.</td></tr>';
    return;
  }
  if (!hasPermission('ventas.manage') && !hasPermission('orders.read')) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, { title: 'Sin permiso', hint: 'Tu rol no puede ver solicitudes comerciales.' })
      : '<tr><td colspan="8">No tienes permiso para ver solicitudes comerciales.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const status = document.getElementById('sol-filter-status')?.value ?? 'activas';
  const qText = (document.getElementById('sol-filter-q')?.value || '').trim();
  const q = new URLSearchParams({ limit: 50, offset: 0 });
  if (status) q.set('status', status);
  if (qText) q.set('q', qText);
  const r = await fetch(API + '/solicitudes?' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="8">${data.message || 'Error'}</td></tr>`;
    return;
  }
  solicitudesState.requests = data.requests || [];
  solicitudesState.total = data.total || 0;
  if (meta) {
    meta.textContent = status === 'activas'
      ? `${data.total || 0} pendientes de gestión`
      : `${data.total || 0} solicitudes`;
  }
  const chips = document.getElementById('ventas-chips');
  if (chips) {
    const rows = solicitudesState.requests;
    let awaitPay = 0, awaitShip = 0, awaitDeliver = 0;
    rows.forEach(req => {
      const pay = req.payment_status || 'pendiente_pago';
      if (pay === 'pendiente_pago' && ['aprobada', 'en_revision', 'pendiente'].includes(req.status)) awaitPay++;
      if (req.status === 'convertida' && ['pagado', 'credito'].includes(pay)) awaitShip++;
      if (req.status === 'enviada') awaitDeliver++;
    });
    chips.innerHTML = `
      <span class="ops-chip"><span>En lista</span><strong>${data.total || 0}</strong></span>
      <span class="ops-chip ops-chip--warn"><span>Esperan pago</span><strong>${awaitPay}</strong></span>
      <span class="ops-chip"><span>Por enviar</span><strong>${awaitShip}</strong></span>
      <span class="ops-chip"><span>En tránsito</span><strong>${awaitDeliver}</strong></span>`;
  }
  if (!solicitudesState.requests.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, {
          title: status === 'activas' ? 'Sin pendientes' : 'Sin resultados',
          hint: status === 'activas'
            ? 'Espera una compra desde la Vitrina o revisa el historial con otro filtro.'
            : 'Prueba otro estado o limpia la búsqueda.',
          ctaLabel: 'Ir a Vitrina',
          ctaOnclick: "showPage('tienda')",
        })
      : `<tr><td colspan="8">${status === 'activas' ? 'No hay solicitudes pendientes.' : 'Sin solicitudes con este filtro.'}</td></tr>`;
    refreshVentasBadge();
    return;
  }
  body.innerHTML = solicitudesState.requests.map(req => {
    const lines = (req.lines || []).map(l => `${l.product_name || l.product_id} ×${l.quantity}`).join(', ');
    return `<tr>
      <td>${req.request_id}</td>
      <td>${req.client_name}<br><span style="font-size:10px;color:var(--muted)">${req.client_email}</span></td>
      <td>${lines}</td>
      <td><span class="${solicitudStatusClass(req.status)}">${solicitudStatusLabel(req.status)}</span></td>
      <td>${paymentBadge(req.payment_status)}</td>
      <td>${req.created_at || '—'}</td>
      <td>${req.order_id || req.tracking_number || '—'}</td>
      <td>${solicitudActions(req)}</td>
    </tr>`;
  }).join('');
  refreshVentasBadge();
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
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function setSolicitudPago(id, payment_status) {
  if (payment_status === 'pagado') {
    alert('Solo el cliente puede marcar el pedido como pagado (Mis pedidos → Pagar).');
    return;
  }
  const r = await fetch(`${API}/solicitudes/${id}/pago`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ payment_status }),
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  await loadSolicitudes();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function devolverSolicitud(id) {
  const err = document.getElementById('devolver-error');
  if (err) err.textContent = '';
  const hid = document.getElementById('devolver-request-id');
  if (hid) hid.value = String(id);
  const reason = document.getElementById('devolver-reason');
  if (reason) reason.value = '';
  const cond = document.getElementById('devolver-condition');
  if (cond) cond.value = 'apto';
  window._devolverLines = [];
  try {
    const r = await fetch(`${API}/solicitudes/${id}`, { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) { alert(data.message || 'No se pudo cargar la solicitud'); return; }
    const req = data.request || {};
    const lines = req.lines || [];
    const stock = req.stock_lines || [];
    const byPid = {};
    stock.forEach(s => { byPid[String(s.product_id || '')] = s; });
    window._devolverLines = lines.map(l => {
      const st = byPid[String(l.product_id || '')] || stock.find(s => Number(s.variant_id) === Number(l.variant_id));
      const vid = Number((st && st.variant_id) || l.variant_id || 0);
      const qty = Number(l.quantity || (st && st.quantity) || 0);
      return {
        variant_id: vid,
        quantity: qty,
        label: l.product_name || l.sku || (`#${l.product_id || vid}`),
      };
    }).filter(l => l.variant_id >= 1 && l.quantity >= 1);
    if (!window._devolverLines.length && stock.length) {
      window._devolverLines = stock.map(s => ({
        variant_id: Number(s.variant_id),
        quantity: Number(s.quantity || 0),
        label: `Variante ${s.variant_id}`,
      })).filter(l => l.variant_id >= 1 && l.quantity >= 1);
    }
  } catch (e) {
    alert('Error de red al cargar la solicitud');
    return;
  }
  renderDevolverLines();
  onDevolverConditionChange();
  const m = document.getElementById('devolver-modal');
  if (m) {
    m.hidden = false;
    m.setAttribute('aria-hidden', 'false');
  }
}

function closeDevolverModal() {
  const m = document.getElementById('devolver-modal');
  if (!m) return;
  m.hidden = true;
  m.setAttribute('aria-hidden', 'true');
}

function onDevolverConditionChange() {
  const cond = document.getElementById('devolver-condition')?.value || 'apto';
  const block = document.getElementById('devolver-mixto-block');
  if (block) block.hidden = cond !== 'mixto';
}

function renderDevolverLines() {
  const body = document.getElementById('devolver-lines-body');
  if (!body) return;
  const rows = window._devolverLines || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="4">Sin líneas de stock para inspeccionar.</td></tr>';
    return;
  }
  body.innerHTML = rows.map((l, i) => `
    <tr data-vid="${l.variant_id}">
      <td>${l.label}</td>
      <td>${l.quantity}</td>
      <td><input type="number" min="0" max="${l.quantity}" value="${l.quantity}" id="dev-ok-${i}" style="width:64px" /></td>
      <td><input type="number" min="0" max="${l.quantity}" value="0" id="dev-bad-${i}" style="width:64px" /></td>
    </tr>`).join('');
}

async function confirmDevolverSolicitud() {
  const id = parseInt(document.getElementById('devolver-request-id')?.value || '0', 10);
  const condition = document.getElementById('devolver-condition')?.value || '';
  const reason = (document.getElementById('devolver-reason')?.value || '').trim();
  const err = document.getElementById('devolver-error');
  if (!id) return;
  const payload = { condition, reason };
  if (condition === 'mixto') {
    const lines = window._devolverLines || [];
    const inspections = [];
    for (let i = 0; i < lines.length; i++) {
      const ok = parseInt(document.getElementById('dev-ok-' + i)?.value || '0', 10);
      const bad = parseInt(document.getElementById('dev-bad-' + i)?.value || '0', 10);
      if (ok + bad !== lines[i].quantity) {
        if (err) err.textContent = `Línea "${lines[i].label}": apto + dañado debe ser ${lines[i].quantity}.`;
        return;
      }
      inspections.push({ variant_id: lines[i].variant_id, restock_qty: ok, damaged_qty: bad });
    }
    payload.inspections = inspections;
  }
  if (err) err.textContent = '';
  const r = await fetch(`${API}/solicitudes/${id}/devolver`, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) {
    if (err) err.textContent = data.message || 'Error';
    else alert(data.message || 'Error');
    return;
  }
  closeDevolverModal();
  alert(data.message || 'Devolución registrada');
  await loadSolicitudes();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function convertirSolicitud(id) {
  if (!confirm('¿Convertir esta solicitud en venta (landing sales_records)? El Tablero estratégico se actualiza tras Construir modelo / ELT.')) return;
  const r = await fetch(`${API}/solicitudes/${id}/convertir`, {
    method: 'POST', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) {
    if (typeof opsToast === 'function') opsToast(data.message || 'Error', 'danger');
    else alert(data.message || 'Error');
    return;
  }
  const synced = data.analytics_sync && data.analytics_sync.synced;
  const msg = data.analytics_stale
    ? `Venta ${data.order_id} en landing. Sync a Tablero pendiente.`
    : `Venta ${data.order_id} creada${synced ? ` y sincronizada (${synced} hechos)` : ''}.`;
  if (typeof opsToast === 'function') {
    if (data.analytics_stale) {
      opsToast(msg, 'warn', {
        actionLabel: 'Sincronizar ahora',
        action: () => { if (typeof syncStaleAnalytics === 'function') syncStaleAnalytics(); },
      });
    } else {
      opsToast(msg, 'ok');
    }
  } else if (data.analytics_stale && confirm(msg + '\n\n¿Sincronizar ahora?')) {
    if (typeof syncStaleAnalytics === 'function') syncStaleAnalytics();
  } else {
    alert(msg);
  }
  await loadSolicitudes();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

async function loadVentasMastersForForm() {
  /* reservado */
}

window.refreshVentasBadge = refreshVentasBadge;
