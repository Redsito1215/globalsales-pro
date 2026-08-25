/* Detalle de solicitud + PDF (q3-ventas.js ya define solicitudStatusLabel/Class) */

function showSolicitudDetailModal(show) {
  const m = document.getElementById('solicitud-detail-modal');
  if (!m) return;
  m.hidden = !show;
  m.setAttribute('aria-hidden', show ? 'false' : 'true');
}

function openSolicitudPdf(id) {
  window.open(`${API}/soporte/solicitudes/${id}/factura.pdf`, '_blank', 'noopener');
}

async function showPaymentReceipt(id) {
  const r = await fetch(`${API}/solicitudes/${id}/comprobante`, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'No se pudo cargar el comprobante.'); return; }
  const x = data.receipt || {};
  const card = x.card || {};
  const message = `${x.transaction_reference}\n${x.invoice_number}\nTarjeta ${card.brand || ''} •••• ${card.last4 || ''}\nTotal: $${Number(x.amount || 0).toFixed(2)}\nFecha: ${(x.paid_at || '').replace('T', ' ').slice(0, 19)}`;
  if (typeof opsConfirm === 'function') await opsConfirm({ title: 'Comprobante de pago', message, confirmLabel: 'Cerrar' });
}

async function openSolicitudDetail(id) {
  const body = document.getElementById('sol-detail-body');
  const title = document.getElementById('sol-detail-title');
  if (!body) return;
  showSolicitudDetailModal(true);
  if (title) title.textContent = `Solicitud #${id}`;
  body.innerHTML = '<p class="modal-sub">Cargando detalle…</p>';
  try {
    const r = await fetch(`${API}/solicitudes/${id}`, { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) {
      showSolicitudDetailModal(false);
      notifyErr(data.message || 'Error al cargar la solicitud');
      return;
    }
    const req = data.request;
    if (!req) {
      showSolicitudDetailModal(false);
      notifyErr('Respuesta inválida del servidor.');
      return;
    }
    const labelFn = typeof solicitudStatusLabel === 'function' ? solicitudStatusLabel : (s => s || '—');
    const classFn = typeof solicitudStatusClass === 'function' ? solicitudStatusClass : (() => 'badge');
    if (title) {
      title.textContent = req.client_order_no
        ? `Pedido ${req.client_order_no}`
        : `Solicitud #${req.request_id}`;
    }
    const lines = (req.lines || []).map(l => {
      const gross = Number(l.line_gross != null ? l.line_gross : (Number(l.unit_price || 0) * Number(l.quantity || 0)));
      const net = Number(l.line_net != null ? l.line_net : gross);
      const disc = Number(l.discount_alloc || 0);
      return `<tr><td>${l.product_name || l.product_id}</td><td>${l.quantity}</td><td>$${Number(l.unit_price || 0).toFixed(2)}</td><td>${disc ? '-$' + disc.toFixed(2) : '—'}</td><td>$${net.toFixed(2)}</td></tr>`;
    }).join('');
    const pay = req.payment_status || 'pendiente_pago';
    const payLabel = (typeof paymentLabel === 'function') ? paymentLabel(pay) : pay;
    const canManage = typeof hasPermission === 'function' && hasPermission('ventas.manage');
    body.innerHTML = `
    <div class="detail-grid">
      <div><span class="detail-label">Cliente</span><strong>${req.client_name || '—'}</strong><br><span style="color:var(--muted);font-size:12px">${req.client_email || ''}${req.client_phone ? ' · ' + req.client_phone : ''}</span></div>
      <div><span class="detail-label">Estado</span><span class="${classFn(req.status)}">${labelFn(req.status)}</span></div>
      <div><span class="detail-label">Pago</span>${typeof paymentBadge === 'function' ? paymentBadge(pay) : payLabel}</div>
      <div><span class="detail-label">Fecha</span>${req.created_at || '—'}</div>
      <div><span class="detail-label">País destino</span>${req.country_name || req.country_id || '—'}</div>
      ${req.shipping_destination ? `<div><span class="detail-label">Destino</span>${req.shipping_destination}</div>` : ''}
      <div><span class="detail-label">Canal</span>${req.channel_name || req.channel_id || '—'}</div>
      <div><span class="detail-label">Pedido venta</span>${req.order_id || '—'}</div>
      ${req.tracking_number ? `<div><span class="detail-label">Seguimiento</span><code>${req.tracking_number}</code></div>` : ''}
      ${req.shipped_at ? `<div><span class="detail-label">Enviado</span>${req.shipped_at}</div>` : ''}
      ${req.delivered_at ? `<div><span class="detail-label">Entregado</span>${req.delivered_at}</div>` : ''}
      ${req.paid_at ? `<div><span class="detail-label">Pagado el</span>${req.paid_at}</div>` : ''}
      ${req.refund_status ? `<div><span class="detail-label">Reembolso</span>${req.refund_status.replaceAll('_', ' ')} · $${Number(req.return_refund_amount || 0).toFixed(2)}</div>` : ''}
      ${req.status === 'devuelta' ? `<div><span class="detail-label">Devolución</span>${req.return_condition || '—'} · apto ${req.return_restock_units ?? 0} · dañado ${req.return_damaged_units ?? 0}</div>` : ''}
    </div>
    ${req.return_reason ? `<p class="modal-sub"><strong>Motivo devolución:</strong> ${req.return_reason}</p>` : ''}
    ${req.notes ? `<p class="modal-sub"><strong>Notas:</strong> ${req.notes}</p>` : ''}
    <table class="detail-table"><thead><tr><th>Producto</th><th>Cant.</th><th>P.unit.</th><th>Desc.</th><th>Neto</th></tr></thead><tbody>${lines || '<tr><td colspan="5">Sin líneas</td></tr>'}</tbody></table>
    <div class="detail-totals">
      <div>Subtotal: $${Number(req.subtotal || 0).toFixed(2)}</div>
      ${Number(req.shipping_cost || 0) > 0 ? `<div>Envío: $${Number(req.shipping_cost).toFixed(2)}${req.shipping_region ? ` (${req.shipping_region})` : ''}</div>` : ''}
      ${req.discount_code ? `<div>Descuento <code>${req.discount_code}</code>: -$${Number(req.discount_amount || 0).toFixed(2)}</div>` : ''}
      <div><strong>Total:</strong> $${Number(req.total || req.subtotal || 0).toFixed(2)}</div>
    </div>
    ${pay === 'pagado' ? `<button type="button" class="btn btn-ghost btn-sm" onclick="showPaymentReceipt(${id})">Ver comprobante de pago</button>` : ''}
    ${canManage && !['rechazada','cancelada'].includes(req.status) && pay === 'pendiente_pago' ? `
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <span class="modal-sub" style="margin:0">${req.status === 'aprobada'
          ? 'El cliente debe pagar con tarjeta en Mis pedidos antes de continuar.'
          : 'Aprueba la solicitud para que el cliente pueda pagar en Mis pedidos.'}</span>
      </div>` : ''}
    <div id="sol-detail-audit" style="margin-top:14px"></div>`;
    const pdfBtn = document.getElementById('sol-detail-pdf');
    if (pdfBtn) pdfBtn.onclick = () => openSolicitudPdf(id);
    const auditHost = document.getElementById('sol-detail-audit');
    if (auditHost) {
      auditHost.innerHTML = '<p class="modal-sub">Cargando línea de tiempo…</p>';
      try {
        const hr = await fetch(`${API}/solicitudes/${id}/timeline`, { credentials: 'same-origin' });
        const hist = await hr.json();
        const labels = { created: 'Solicitud creada', status_changed: 'Estado actualizado', payment_updated: 'Pago aprobado', payment_failed: 'Intento de pago rechazado', returned: 'Devolución y reembolso' };
        auditHost.innerHTML = `<h3 class="table-title">Línea de tiempo</h3>${(hist.events || []).map(event => `
          <div class="page-meta-strip" style="margin-top:7px"><strong>${labels[event.event_type] || event.event_type}</strong>
          <span> · ${(event.created_at || '').replace('T', ' ').slice(0, 19)}</span></div>`).join('') || '<p class="modal-sub">Sin eventos.</p>'}`;
      } catch {
        auditHost.innerHTML = '';
      }
    }
  } catch (_) {
    showSolicitudDetailModal(false);
    notifyErr('Error de red al cargar la solicitud.');
  }
}

function closeSolicitudDetail() {
  showSolicitudDetailModal(false);
}

window.openSolicitudDetail = openSolicitudDetail;
window.openSolicitudPdf = openSolicitudPdf;
window.showPaymentReceipt = showPaymentReceipt;
window.closeSolicitudDetail = closeSolicitudDetail;
