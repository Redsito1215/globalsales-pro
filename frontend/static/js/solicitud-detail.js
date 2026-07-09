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
      alert(data.message || 'Error al cargar la solicitud');
      return;
    }
    const req = data.request;
    if (!req) {
      showSolicitudDetailModal(false);
      alert('Respuesta inválida del servidor.');
      return;
    }
    const labelFn = typeof solicitudStatusLabel === 'function' ? solicitudStatusLabel : (s => s || '—');
    const classFn = typeof solicitudStatusClass === 'function' ? solicitudStatusClass : (() => 'badge');
    if (title) title.textContent = `Solicitud #${req.request_id}`;
    const lines = (req.lines || []).map(l =>
      `<tr><td>${l.product_name || l.product_id}</td><td>${l.quantity}</td><td>$${Number(l.unit_price || 0).toFixed(2)}</td><td>$${(Number(l.unit_price || 0) * Number(l.quantity || 0)).toFixed(2)}</td></tr>`
    ).join('');
    body.innerHTML = `
    <div class="detail-grid">
      <div><span class="detail-label">Cliente</span><strong>${req.client_name || '—'}</strong><br><span style="color:var(--muted);font-size:12px">${req.client_email || ''}${req.client_phone ? ' · ' + req.client_phone : ''}</span></div>
      <div><span class="detail-label">Estado</span><span class="${classFn(req.status)}">${labelFn(req.status)}</span></div>
      <div><span class="detail-label">Fecha</span>${req.created_at || '—'}</div>
      <div><span class="detail-label">País</span>${req.country_name || req.country_id || '—'}</div>
      <div><span class="detail-label">Canal</span>${req.channel_name || req.channel_id || '—'}</div>
      <div><span class="detail-label">Pedido venta</span>${req.order_id || '—'}</div>
    </div>
    ${req.notes ? `<p class="modal-sub"><strong>Notas:</strong> ${req.notes}</p>` : ''}
    <table class="detail-table"><thead><tr><th>Producto</th><th>Cant.</th><th>P.unit.</th><th>Total</th></tr></thead><tbody>${lines || '<tr><td colspan="4">Sin líneas</td></tr>'}</tbody></table>
    <div class="detail-totals">
      ${req.discount_code ? `<div>Descuento <code>${req.discount_code}</code>: -$${Number(req.discount_amount || 0).toFixed(2)}</div>` : ''}
      <div><strong>Total estimado:</strong> $${Number(req.total || req.subtotal || 0).toFixed(2)}</div>
    </div>`;
    const pdfBtn = document.getElementById('sol-detail-pdf');
    if (pdfBtn) pdfBtn.onclick = () => openSolicitudPdf(id);
  } catch (_) {
    showSolicitudDetailModal(false);
    alert('Error de red al cargar la solicitud.');
  }
}

function closeSolicitudDetail() {
  showSolicitudDetailModal(false);
}

window.openSolicitudDetail = openSolicitudDetail;
window.openSolicitudPdf = openSolicitudPdf;
window.closeSolicitudDetail = closeSolicitudDetail;
