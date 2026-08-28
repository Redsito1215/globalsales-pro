/* Q2 Análisis — previsualización y exportación PDF */
function analysisExportParams() {
  const q = new URLSearchParams();
  const region = document.getElementById('an-region')?.value;
  const country = document.getElementById('an-country')?.value;
  const item = document.getElementById('an-itemtype')?.value;
  const channel = document.getElementById('an-channel')?.value;
  const priority = document.getElementById('an-priority')?.value;
  const months = document.getElementById('an-months')?.value;
  const limit = document.getElementById('an-limit')?.value || '5000';
  if (region) q.set('region', region);
  if (country) q.set('country', country);
  if (item) q.set('item_type', item);
  if (channel) q.set('channel', channel);
  if (priority) q.set('priority', priority);
  if (months) q.set('months', months);
  q.set('limit', limit);
  return q;
}

function analysisPreviewValue(value) {
  if (value == null || value === '') return '—';
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function parseAnalysisCsvPreview(text) {
  const lines = String(text || '').replace(/^\uFEFF/, '').split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];
  const parseLine = line => {
    const cells = []; let cell = ''; let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (ch === '"' && line[i + 1] === '"' && quoted) { cell += '"'; i += 1; }
      else if (ch === '"') quoted = !quoted;
      else if (ch === ',' && !quoted) { cells.push(cell); cell = ''; }
      else cell += ch;
    }
    cells.push(cell); return cells;
  };
  const headers = parseLine(lines[0]);
  return lines.slice(1, 26).map(line => {
    const cells = parseLine(line); const row = {};
    headers.forEach((header, index) => { row[header] = cells[index] ?? ''; });
    return row;
  });
}

function closeAnalysisPreview() {
  const box = document.getElementById('export-preview');
  if (box) { box.hidden = true; box.setAttribute('aria-hidden', 'true'); }
  document.body.classList.remove('modal-open');
}

async function previewAnalysisExport() {
  if (!window._authUser) {
    notifyWarn('Debes iniciar sesión para previsualizar la exportación.');
    openLoginModal();
    return;
  }
  if (!hasPermission('analysis.export')) {
    notifyWarn('Tu rol no incluye permiso para exportar PDF.');
    return;
  }
  const st = document.getElementById('export-status');
  const box = document.getElementById('export-preview');
  if (box && box.parentElement !== document.body) document.body.appendChild(box);
  if (st) st.textContent = 'Preparando vista previa…';
  const q = analysisExportParams();
  let r = await fetch(API + '/analysis/preview?' + q, { credentials: 'same-origin' });
  let data;
  if (r.ok) {
    data = await r.json();
  } else if (r.status === 404) {
    r = await fetch(API + '/analysis/export?' + q, { credentials: 'same-origin' });
    if (!r.ok) { notifyErr('No se pudo generar la vista previa.'); return; }
    const text = await r.text();
    const fallbackRows = parseAnalysisCsvPreview(text);
    const exported = Number(r.headers.get('X-Export-Rows') || fallbackRows.length);
    data = { rows: fallbackRows, preview_count: fallbackRows.length, export_count: exported, truncated: r.headers.get('X-Export-Truncated') === '1' };
  } else {
    data = await r.json().catch(() => ({}));
    notifyErr(data.message || 'No se pudo generar la vista previa.');
    return;
  }
  const rows = data.rows || [];
  const preferred = ['order_id','country','region','item_type','sales_channel','order_priority','order_date','units_sold','total_revenue','total_profit'];
  const columns = rows.length ? preferred.filter(k => k in rows[0]) : [];
  const labels = {order_id:'Pedido',country:'País',region:'Región',item_type:'Categoría',sales_channel:'Canal',order_priority:'Prioridad',order_date:'Fecha',units_sold:'Unidades',total_revenue:'Ingreso',total_profit:'Utilidad'};
  document.getElementById('export-preview-head').innerHTML = columns.length
    ? `<tr>${columns.map(k => `<th>${labels[k] || k}</th>`).join('')}</tr>` : '<tr><th>Resultado</th></tr>';
  document.getElementById('export-preview-body').innerHTML = rows.length
    ? rows.map(row => `<tr>${columns.map(k => `<td>${analysisPreviewValue(row[k])}</td>`).join('')}</tr>`).join('')
    : '<tr><td>No hay datos con los filtros seleccionados.</td></tr>';
  document.getElementById('export-preview-meta').textContent = `${data.export_count || 0} filas se descargarán · se muestran ${data.preview_count || 0}`;
  box.hidden = false;
  box.setAttribute('aria-hidden', 'false');
  const scroll = box.querySelector('.table-scroll');
  if (scroll) { scroll.scrollTop = 0; scroll.scrollLeft = 0; }
  document.body.classList.add('modal-open');
  if (st) st.textContent = data.truncated ? 'La descarga se limitará al máximo seleccionado.' : 'Revisa la muestra antes de descargar.';
  box.querySelector('.modal-x')?.focus();
}

async function exportAnalysis() {
  if (!window._authUser || !hasPermission('analysis.export')) return;
  const st = document.getElementById('export-status');
  if (st) st.textContent = 'Exportando…';
  const q = analysisExportParams();
  const r = await fetch(API + '/analysis/export/pdf?' + q, { credentials: 'same-origin' });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    if (st) st.textContent = d.message || 'Error al exportar';
    notifyErr(d.message || 'Error al exportar');
    return;
  }
  const blob = await r.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'altavia_trade_ventas.pdf';
  a.click();
  URL.revokeObjectURL(a.href);
  closeAnalysisPreview();
  const msg = 'PDF descargado con los filtros seleccionados.';
  if (st) st.textContent = msg;
  if (typeof opsToast === 'function') opsToast(msg, 'ok');
}

window.previewAnalysisExport = previewAnalysisExport;
window.closeAnalysisPreview = closeAnalysisPreview;

async function loadAnalisisExportPage() {
  const st = document.getElementById('export-status');
  if (st) {
    st.textContent = window._authUser
      ? 'Listo. Exporta hasta el límite elegido (máx. 50 000). El periodo se ancla al histórico del DW.'
      : 'Inicia sesión como analista o administrador.';
  }
}
