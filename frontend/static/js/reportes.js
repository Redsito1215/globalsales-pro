/* Informes simples y compuestos — UI para el usuario final */
const REPORT_LABELS = {
  request_id: 'N.º solicitud',
  client_name: 'Cliente',
  client_email: 'Correo',
  status: 'Estado',
  payment_status: 'Pago',
  total: 'Total',
  created_at: 'Fecha',
  sku: 'Código',
  product_name: 'Producto',
  inventory_quantity: 'Existencias',
  unit_price: 'Precio',
  unit_cost: 'Costo',
  vendor_name: 'Proveedor',
  thread_email: 'Cliente',
  last_body: 'Último mensaje',
  last_at: 'Fecha',
  message_count: 'Mensajes',
  espera_respuesta: 'Espera respuesta',
  po_id: 'Orden',
  notes: 'Notas',
  received_at: 'Recibida',
  vendor_id: 'Código',
  name: 'Nombre',
  country: 'País',
  email: 'Correo',
  phone: 'Teléfono',
  active: 'Activo',
  order_id: 'N.º venta',
  tracking: 'Seguimiento',
  shipped_at: 'Enviado',
  code: 'Cupón',
  discount_type: 'Tipo',
  value: 'Valor',
  uses: 'Usos',
  max_uses: 'Límite',
  role: 'Rol',
  category: 'Categoría',
  reviewed_by: 'Revisó',
};

const RC_LABELS = {
  mes: 'Mes',
  categoria: 'Categoría',
  pedidos: 'Pedidos',
  unidades: 'Unidades',
  ingresos: 'Ingresos',
  utilidad: 'Utilidad',
  ranking: '#',
  grupo: 'Grupo',
  concepto: 'Concepto',
  monto: 'Monto',
  detalle: 'Detalle',
  unidades_vendidas: 'Unidades vendidas',
  stock_actual: 'Existencias actuales',
  rotacion_aprox: 'Rotación aprox.',
  region: 'Región',
  dias_promedio: 'Días promedio',
  cupon: 'Cupón',
  usos_landing: 'Usos',
  ingresos_con_cupon: 'Ingresos c/cupón',
  descuento_total: 'Descuento',
  activo: 'Activo',
  costos: 'Costos',
  margen_pct: 'Margen %',
  producto: 'Producto',
  ventas: 'Ventas',
  compras: 'Compras',
  diferencia: 'Diferencia',
  dias_cobertura: 'Días de cobertura',
  mediana_dias: 'Mediana (días)',
  cumplimiento_pct: 'Cumplimiento %',
  usos: 'Usos',
  ingreso_neto: 'Ingreso neto',
  proveedor: 'Proveedor',
  ordenes: 'Órdenes',
  participacion_pct: 'Participación %',
  ticket_promedio: 'Ticket promedio',
  riesgo: 'Riesgo',
  decision: 'Decisión',
  retorno_pct: 'Retorno %',
  indicador: 'Indicador',
  valor: 'Valor',
  estado: 'Estado',
};

function reportHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));
}

/** Catálogo local: el selector siempre tiene texto aunque falle el API de listado */
const RC_FALLBACK_CATALOG = [
  { id: 'RC-01', name: 'Ventas por mes y por categoría de producto', para_que: 'Cruza ventas con inventario para ver evolución y stock por categoría.', quien: 'Gerente general, analista' },
  { id: 'RC-02', name: 'Top 10 productos que más se venden y top 10 que menos se venden', para_que: 'Cruza ventas con inventario para detectar líderes, rezagados y stock disponible.', quien: 'Gerente comercial, analista' },
  { id: 'RC-03', name: 'Balanza interna: cuánto se vendió frente a cuánto se compró', para_que: 'Comparar ventas frente a compras recibidas.', quien: 'Jefe de compras, gerencia' },
  { id: 'RC-04', name: 'Qué tan rápido rota el inventario por categoría', para_que: 'Cruzar unidades vendidas con stock actual.', quien: 'Jefe de inventario' },
  { id: 'RC-05', name: 'Tiempo promedio entre pedir y enviar, por país o región', para_que: 'Cruza logística con ventas para medir cumplimiento e ingresos asociados.', quien: 'Jefe de logística' },
  { id: 'RC-06', name: 'Cuánto se usan los cupones y cómo afectan las ventas', para_que: 'Medir uso de cupones e impacto en ingresos.', quien: 'Gerente comercial' },
  { id: 'RC-07', name: 'Ganancia (margen) por categoría de producto en el tiempo', para_que: 'Cruza ventas con inventario para revisar margen y cobertura por categoría.', quien: 'Gerente, analista' },
  { id: 'RC-08', name: 'Estado de la carga de datos para informes', para_que: 'Cruza estado de carga con conteos de ventas, compras, inventario y logística.', quien: 'Administrador, analista' },
  { id: 'RC-09', name: 'Compras mayoristas por proveedor', para_que: 'Cruza compras con utilidad de ventas asociada al proveedor.', quien: 'Gerencia, compras' },
  { id: 'RC-10', name: 'Dependencia estratégica por proveedor', para_que: 'Detectar concentración de abastecimiento y riesgo gerencial.', quien: 'Gerencia, compras' },
  { id: 'RC-11', name: 'Rentabilidad por proveedor', para_que: 'Cruza ventas con compras para ver proveedores con mayor utilidad.', quien: 'Gerencia, compras, analista' },
  { id: 'RC-12', name: 'Compras vs utilidad por proveedor', para_que: 'Comparar inversión en compras frente a utilidad generada.', quien: 'Gerencia, compras' },
  { id: 'RC-13', name: 'Productos más rentables por proveedor', para_que: 'Cruza ventas con inventario para decidir impulso, reposición o negociación.', quien: 'Gerencia comercial, compras' },
];

let reportesCatalog = [];
let rcCatalog = [];
let rcUsingFallback = false;
let lastReporteGrid = { id: '', columns: [], rows: [], labels: REPORT_LABELS };
let lastRcGrid = { id: '', columns: [], rows: [], labels: RC_LABELS };
let rcFilterOptionsLoaded = false;
let pendingRcReportId = '';

function reportesApiBase() {
  if (typeof API === 'string' && API) return API;
  if (typeof window !== 'undefined' && window.API) return window.API;
  return (window.location.origin || '') + '/api';
}

function reportNotify(message, type) {
  if (typeof window.notify === 'function') {
    window.notify(message, type || 'info');
    return;
  }
  if (typeof window.opsToast === 'function') {
    window.opsToast(message, type || 'info');
    return;
  }
  console.warn(message);
}

function shortReportLabel(rep) {
  if (!rep) return '';
  const id = rep.id || '';
  const name = (rep.name || '').trim();
  if (!name) return id;
  const max = 72;
  const clipped = name.length > max ? name.slice(0, max - 1) + '…' : name;
  return id ? `${id} — ${clipped}` : clipped;
}

function reportBusinessArea(rep) {
  const text = `${rep?.name || ''} ${rep?.para_que || ''}`.toLowerCase();
  if (/inventario|stock|sku|rotaci[oó]n|cobertura/.test(text)) return 'Inventario';
  if (/compra|proveedor/.test(text)) return 'Compras';
  if (/log[ií]stic|env[ií]o|despacho|entrega/.test(text)) return 'Logística';
  if (/cup[oó]n|promoci[oó]n|descuento/.test(text)) return 'Marketing';
  if (/pago|caja|margen|rentabilidad|utilidad|devoluci[oó]n/.test(text)) return 'Finanzas';
  if (/usuario|rol|acceso|carga anal[ií]tica/.test(text)) return 'Administración';
  if (/chat|soporte|respuesta/.test(text)) return 'Servicio al cliente';
  return 'Ventas';
}

function fillSelectOptions(sel, catalog) {
  if (!sel) return;
  const options = (catalog || []).map((rep) => {
    const option = document.createElement('option');
    option.value = rep.id;
    option.textContent = shortReportLabel(rep);
    option.dataset.filterArea = reportBusinessArea(rep);
    return option;
  });
  sel.replaceChildren(...options);
  if (sel.options.length) sel.selectedIndex = 0;
}

function setReportMeta(el, rep) {
  if (!el) return;
  if (!rep) {
    el.innerHTML = '';
    return;
  }
  const para = rep.para_que || '';
  const quien = rep.quien || '';
  el.innerHTML =
    (para ? `<span>${para}</span>` : '') +
    (quien ? `<br><span class="report-audience">Para: ${quien}</span>` : '');
}

function setExportStatus(id, message, show) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!show) {
    el.hidden = true;
    el.textContent = '';
    return;
  }
  el.hidden = false;
  el.textContent = message || '';
}

function setExportBusy(buttonIds, busy) {
  (buttonIds || []).forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = !!busy;
  });
}

function setRcFallbackBanner(show) {
  const banner = document.getElementById('rc-fallback-banner');
  if (!banner) return;
  if (!show) {
    banner.hidden = true;
    banner.textContent = '';
    return;
  }
  banner.hidden = false;
  banner.textContent = 'Usando catálogo local — el listado del servidor no respondió. Puedes seguir; reinicia la app si el detalle falla.';
}

function emptyTableHtml(cols, message, showModelCta) {
  const span = cols || 1;
  const cta = showModelCta
    ? `<div class="report-empty-cta"><button type="button" class="btn btn-primary btn-sm" onclick="typeof goConstruirModelo==='function'&&goConstruirModelo()">Ir a Construir modelo / ELT</button> <span class="catalog-meta">o dispara el DAG Airflow <code>globtrade_strategic_etl</code></span></div>`
    : '';
  return `<tr><td colspan="${span}">${message || 'Sin datos para este informe.'}${cta}</td></tr>`;
}

function needsModelCta(reportId, message) {
  if (!reportId || reportId === 'RC-08') return false;
  if (!/^RC-0[1-7]$/.test(reportId)) return false;
  const m = String(message || '').toLowerCase();
  return !message || m.includes('fact_ventas') || m.includes('vacío') || m.includes('vacio') || m.includes('modelo') || m.includes('sin datos');
}

function csvEscape(value) {
  const s = value == null ? '' : String(value);
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function downloadCsv(filename, columns, rows, labels) {
  const labelMap = labels || {};
  const header = columns.map((c) => csvEscape(labelMap[c] || c)).join(',');
  const lines = (rows || []).map((row) =>
    columns
      .map((c) => {
        let v = row[c];
        if (typeof v === 'boolean') v = v ? 'Sí' : 'No';
        return csvEscape(v == null ? '' : v);
      })
      .join(',')
  );
  const bom = '\ufeff';
  const blob = new Blob([bom + [header, ...lines].join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function loadReportesPage() {
  const sel = document.getElementById('reportes-select');
  const meta = document.getElementById('reportes-meta');
  if (!sel) return;
  try {
    const r = await fetch(reportesApiBase() + '/reportes', { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (meta) meta.textContent = data.message || 'No se pudieron cargar los informes.';
      sel.innerHTML = '';
      return;
    }
    reportesCatalog = data.reports || [];
    const prev = sel.value;
    fillSelectOptions(sel, reportesCatalog);
    if (prev && reportesCatalog.some((x) => x.id === prev)) sel.value = prev;
    if (!reportesCatalog.length) {
      if (meta) meta.textContent = 'No hay informes disponibles.';
      return;
    }
    onReportesSelect();
    await loadReporteActual();
  } catch (e) {
    if (meta) meta.textContent = e.message || 'Error al cargar informes';
  }
}

function onReportesSelect() {
  const id = document.getElementById('reportes-select')?.value;
  const thr = document.getElementById('reportes-thr-wrap');
  if (thr) thr.hidden = id !== 'RS-03';
  const rep = reportesCatalog.find((x) => x.id === id);
  const title = document.getElementById('reportes-title');
  const meta = document.getElementById('reportes-meta');
  if (title) title.textContent = rep ? rep.name : 'Informe';
  setReportMeta(meta, rep);
}

async function loadReporteActual() {
  const id = document.getElementById('reportes-select')?.value;
  const body = document.getElementById('reportes-body');
  const head = document.getElementById('reportes-head');
  const count = document.getElementById('reportes-count');
  if (!id || !body || !head) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  lastReporteGrid = { id, columns: [], rows: [], labels: REPORT_LABELS };
  const q = document.getElementById('reportes-q')?.value || '';
  const thr = document.getElementById('reportes-thr')?.value || '20';
  let url = `${reportesApiBase()}/reportes/${encodeURIComponent(id)}?limit=200`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (id === 'RS-03') url += `&threshold=${encodeURIComponent(thr)}`;
  try {
    const r = await fetch(url, { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      body.innerHTML = emptyTableHtml(8, data.message || 'No se pudo cargar el informe.');
      return;
    }
    const cols = (data.report && data.report.columns) || data.columns || [];
    const rows = data.rows || [];
    lastReporteGrid = { id, columns: cols, rows, labels: REPORT_LABELS };
    head.innerHTML = `<tr>${cols.map((c) => `<th>${REPORT_LABELS[c] || c}</th>`).join('')}</tr>`;
    if (!rows.length) {
      const msg = data.message || 'Sin datos para este informe.';
      body.innerHTML = emptyTableHtml(cols.length || 1, msg, false);
    } else {
      body.innerHTML = rows
        .map((row) => {
          const tds = cols
            .map((c) => {
              let v = row[c];
              if (typeof v === 'boolean') v = v ? 'Sí' : 'No';
              return `<td>${v == null || v === '' ? '—' : String(v)}</td>`;
            })
            .join('');
          return `<tr>${tds}</tr>`;
        })
        .join('');
    }
    if (count) count.textContent = `${data.total ?? rows.length} fila(s)`;
    onReportesSelect();
  } catch (e) {
    body.innerHTML = emptyTableHtml(8, e.message || 'Error al procesar');
  }
}

async function loadRcPage() {
  const sel = document.getElementById('rc-select');
  const meta = document.getElementById('rc-meta');
  if (!sel) return;

  rcUsingFallback = true;
  rcCatalog = RC_FALLBACK_CATALOG.slice();
  fillSelectOptions(sel, rcCatalog);
  setRcFallbackBanner(false);
  onRcSelect();

  try {
    const r = await fetch(reportesApiBase() + '/compuestos', { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (r.ok && Array.isArray(data.reports) && data.reports.length) {
      rcUsingFallback = false;
      setRcFallbackBanner(false);
      rcCatalog = data.reports;
      const prev = pendingRcReportId || sel.value;
      fillSelectOptions(sel, rcCatalog);
      if (prev && rcCatalog.some((x) => x.id === prev)) sel.value = prev;
      onRcSelect();
    } else {
      setRcFallbackBanner(true);
      if (!r.ok && meta) setReportMeta(meta, rcCatalog[0]);
    }
    await loadRcActual();
    pendingRcReportId = '';
  } catch (e) {
    setRcFallbackBanner(true);
    if (meta) meta.textContent = e.message || 'Error al cargar informes';
    await loadRcActual();
    pendingRcReportId = '';
  }
}

function openStrategicReport(reportId, btn) {
  pendingRcReportId = reportId || '';
  const sel = document.getElementById('rc-select');
  if (sel && pendingRcReportId) {
    sel.value = pendingRcReportId;
    if (typeof window.refreshSmartSelect === 'function') window.refreshSmartSelect(sel);
  }
  if (typeof showPage === 'function') showPage('reportes-compuestos', btn || document.querySelector('.nav-item[data-page="reportes-compuestos"]'));
  if (sel && pendingRcReportId) {
    onRcSelect();
    loadRcActual();
    pendingRcReportId = '';
  }
}

function onRcSelect() {
  const id = document.getElementById('rc-select')?.value;
  const rep = rcCatalog.find((x) => x.id === id) || RC_FALLBACK_CATALOG.find((x) => x.id === id);
  const title = document.getElementById('rc-title');
  const meta = document.getElementById('rc-meta');
  if (title) title.textContent = rep ? rep.name : 'Informe';
  setReportMeta(meta, rep);
}

async function loadRcFilterOptions() {
  if (rcFilterOptionsLoaded) return;
  const configs = [
    { id: 'rc-category', table: 'dim_categoria', all: 'Todas', filter: 'category' },
    { id: 'rc-region', table: 'dim_region', all: 'Todas', filter: 'region' },
    { id: 'rc-channel', table: 'dim_canal', all: 'Todos', filter: 'channel' },
  ];
  await Promise.all(configs.map(async (cfg) => {
    const select = document.getElementById(cfg.id);
    if (!select) return;
    const current = select.value;
    let rows = [];
    try {
      const r = await fetch(`${reportesApiBase()}/master/${cfg.table}?limit=200&active=true`, { credentials: 'same-origin' });
      const data = await r.json().catch(() => ({}));
      if (r.ok) rows = data.rows || [];
    } catch (e) {
      rows = [];
    }
    const names = [...new Set(rows.map((row) => row.name || row.title).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
    if (!names.length && cfg.id === 'rc-channel') names.push('Online', 'Offline');
    select.innerHTML = [`<option value="">${cfg.all}</option>`]
      .concat(names.map((name) => `<option value="${rcSafe(name)}" data-filter-${cfg.filter}="${rcSafe(name)}">${rcSafe(name)}</option>`))
      .join('');
    if (current && names.includes(current)) select.value = current;
    if (typeof window.refreshSmartSelect === 'function') window.refreshSmartSelect(select);
  }));
  rcFilterOptionsLoaded = true;
}

function rcFilterQuery() {
  const params = new URLSearchParams();
  const fields = { start: 'rc-start', end: 'rc-end', category: 'rc-category', region: 'rc-region', channel: 'rc-channel' };
  Object.entries(fields).forEach(([key, id]) => {
    const value = document.getElementById(id)?.value?.trim();
    if (value) params.set(key, value);
  });
  return params.toString();
}

function clearReportesAiState() {
  reportesAiState.lastGenerated = null;
  [
    'reportes-ai-rec-prompt',
    'reportes-ai-gen-prompt',
    'reportes-ai-engine',
    'reportes-ai-catalog-meta',
    'reportes-ai-gen-narrative',
    'reportes-ai-gen-meta',
  ].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    if ('value' in el) el.value = '';
    else el.textContent = '';
  });
  const list = document.getElementById('reportes-ai-rec-list');
  if (list) list.innerHTML = '';
  const result = document.getElementById('reportes-ai-gen-result');
  if (result) result.hidden = true;
}

async function clearReportesFilters() {
  const q = document.getElementById('reportes-q');
  const thr = document.getElementById('reportes-thr');
  if (q) q.value = '';
  if (thr) thr.value = '20';
  clearReportesAiState();
  await loadReporteActual();
}

async function clearRcFilters() {
  ['rc-start', 'rc-end', 'rc-category', 'rc-region', 'rc-channel'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  clearReportesAiState();
  if (typeof window.refreshAllSmartSelects === 'function') window.refreshAllSmartSelects();
  await loadRcActual();
}

function rcSafe(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderRcChart(chart, rows) {
  const root = document.getElementById('rc-chart');
  if (!root) return;
  if (!rows?.length) { root.innerHTML = '<div class="rc-chart-empty">No hay datos para representar con estos filtros.</div>'; return; }
  if (chart?.type === 'status') {
    root.innerHTML = `<div class="rc-chart-status">${rows.map((r) => `<article><small>${rcSafe(r.indicador)}</small><strong>${rcSafe(r.valor)}</strong><span>${rcSafe(r.estado)}</span></article>`).join('')}</div>`;
    return;
  }
  const xKey = chart?.x || Object.keys(rows[0])[0];
  const series = (chart?.series || []).filter((key) => rows.some((row) => Number.isFinite(Number(row[key]))));
  if (!series.length) { root.innerHTML = '<div class="rc-chart-empty">Este informe no contiene series numéricas.</div>'; return; }
  const data = rows.slice(0, 30), width = 1000, height = 300, left = 62, right = 20, top = 24, bottom = 70;
  const plotW = width - left - right, plotH = height - top - bottom;
  const values = data.flatMap((row) => series.map((key) => Number(row[key]) || 0));
  const min = Math.min(0, ...values), max = Math.max(1, ...values), span = max - min || 1;
  const y = (value) => top + (max - value) / span * plotH;
  const colors = ['#0e7490', '#f59e0b', '#7c3aed', '#16a34a'];
  let marks = '', labels = '', legend = '';
  const step = plotW / Math.max(data.length, 1);
  if (chart?.type === 'line') {
    series.forEach((key, si) => {
      const points = data.map((row, i) => `${left + step * (i + .5)},${y(Number(row[key]) || 0)}`).join(' ');
      marks += `<polyline points="${points}" fill="none" stroke="${colors[si % colors.length]}" stroke-width="3"/>`;
    });
  } else {
    const barW = Math.max(3, step * .72 / series.length);
    data.forEach((row, i) => series.forEach((key, si) => {
      const value = Number(row[key]) || 0, x = left + step * i + step * .14 + si * barW, y0 = y(Math.max(0, value)), h = Math.max(1, Math.abs(y(value) - y(0)));
      marks += `<rect x="${x}" y="${y0}" width="${barW - 2}" height="${h}" rx="2" fill="${colors[si % colors.length]}"/>`;
    }));
  }
  data.forEach((row, i) => { if (i % Math.ceil(data.length / 10) === 0) labels += `<text x="${left + step * (i + .5)}" y="${height - 38}" text-anchor="end" transform="rotate(-28 ${left + step * (i + .5)} ${height - 38})" font-size="11" fill="#64748b">${rcSafe(row[xKey]).slice(0, 20)}</text>`; });
  series.forEach((key, i) => { legend += `<circle cx="${left + i * 170}" cy="12" r="5" fill="${colors[i % colors.length]}"/><text x="${left + 10 + i * 170}" y="16" font-size="12" fill="#334155">${rcSafe(RC_LABELS[key] || key)}</text>`; });
  root.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><line x1="${left}" y1="${y(0)}" x2="${width-right}" y2="${y(0)}" stroke="#cbd5e1"/>${legend}${marks}${labels}<text x="8" y="${top+8}" font-size="11" fill="#64748b">${max.toLocaleString('es-EC')}</text><text x="8" y="${top+plotH}" font-size="11" fill="#64748b">${min.toLocaleString('es-EC')}</text></svg>`;
}

async function loadRcActual() {
  await loadRcFilterOptions();
  const id = document.getElementById('rc-select')?.value;
  const body = document.getElementById('rc-body');
  const head = document.getElementById('rc-head');
  const count = document.getElementById('rc-count');
  if (!body || !head) return;
  if (!id) {
    body.innerHTML = '<tr><td colspan="8">Elige un informe en la lista.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const chartRoot = document.getElementById('rc-chart');
  if (chartRoot) chartRoot.innerHTML = '<div class="rc-chart-empty">Cargando visualización…</div>';
  lastRcGrid = { id, columns: [], rows: [], labels: RC_LABELS };
  try {
    const filters = rcFilterQuery();
    const r = await fetch(`${reportesApiBase()}/compuestos/${encodeURIComponent(id)}?limit=120${filters ? `&${filters}` : ''}`, {
      credentials: 'same-origin',
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = data.message || 'No se pudo cargar el informe. Reinicia el servidor de la app e inténtalo de nuevo.';
      body.innerHTML = emptyTableHtml(8, msg, needsModelCta(id, msg));
      renderRcChart(data.chart, []);
      return;
    }
    const cols = (data.report && data.report.columns) || [];
    const rows = data.rows || [];
    lastRcGrid = { id, columns: cols, rows, labels: RC_LABELS };
    renderRcChart(data.chart || data.report?.chart, rows);
    head.innerHTML = `<tr>${cols.map((c) => `<th>${RC_LABELS[c] || c}</th>`).join('')}</tr>`;
    if (!rows.length) {
      const msg = data.message || 'Sin datos para este informe.';
      body.innerHTML = emptyTableHtml(cols.length || 1, msg, needsModelCta(id, msg));
    } else {
      const money = new Set(['ingresos', 'utilidad', 'monto', 'costos', 'ingresos_con_cupon', 'descuento_total']);
      body.innerHTML = rows
        .map((row) => {
          const tds = cols
            .map((c) => {
              let v = row[c];
              if (typeof v === 'boolean') v = v ? 'Sí' : 'No';
              if (money.has(c) && v != null && v !== '') {
                const n = Number(v);
                if (Number.isFinite(n)) {
                  v = n.toLocaleString('es-EC', { style: 'currency', currency: 'USD' });
                }
              }
              return `<td>${v == null || v === '' ? '—' : String(v)}</td>`;
            })
            .join('');
          return `<tr>${tds}</tr>`;
        })
        .join('');
    }
    if (count) count.textContent = `${data.total ?? rows.length} fila(s)`;
    onRcSelect();
  } catch (e) {
    body.innerHTML = emptyTableHtml(8, e.message || 'Error al procesar', needsModelCta(id, e.message));
    renderRcChart(null, []);
  }
}

async function downloadPdf(url, fallbackName) {
  const r = await fetch(url, { credentials: 'same-origin' });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.message || 'No se pudo exportar el PDF.');
  }
  const blob = await r.blob();
  const disposition = r.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/i);
  const filename = (match && match[1]) || fallbackName;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function downloadReportFile(url, fallbackName) {
  const r = await fetch(url, { credentials: 'same-origin' });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.message || 'No se pudo exportar el informe.');
  }
  const blob = await r.blob();
  const disposition = r.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/i);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (match && match[1]) || fallbackName;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function exportReportePdf() {
  const id = document.getElementById('reportes-select')?.value;
  if (!id) return;
  const q = document.getElementById('reportes-q')?.value || '';
  const thr = document.getElementById('reportes-thr')?.value || '20';
  let url = `${reportesApiBase()}/reportes/${encodeURIComponent(id)}/pdf?limit=500`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (id === 'RS-03') url += `&threshold=${encodeURIComponent(thr)}`;
  const btns = ['reportes-btn-pdf'];
  setExportBusy(btns, true);
  setExportStatus('reportes-export-status', 'Generando PDF…', true);
  try {
    await downloadPdf(url, `globtrade-${id}.pdf`);
    setExportStatus('reportes-export-status', 'PDF descargado.', true);
    reportNotify('PDF descargado', 'ok');
  } catch (e) {
    setExportStatus('reportes-export-status', e.message || 'Error al exportar PDF', true);
    reportNotify(e.message || 'Error al exportar PDF', 'danger');
  } finally {
    setExportBusy(btns, false);
  }
}

async function exportRcPdf() {
  const id = document.getElementById('rc-select')?.value;
  if (!id) return;
  const filters = rcFilterQuery();
  const url = `${reportesApiBase()}/compuestos/${encodeURIComponent(id)}/pdf?limit=500${filters ? `&${filters}` : ''}`;
  const btns = ['rc-btn-pdf'];
  setExportBusy(btns, true);
  setExportStatus('rc-export-status', 'Generando PDF…', true);
  try {
    await downloadPdf(url, `globtrade-${id}.pdf`);
    setExportStatus('rc-export-status', 'PDF descargado.', true);
    reportNotify('PDF descargado', 'ok');
  } catch (e) {
    setExportStatus('rc-export-status', e.message || 'Error al exportar PDF', true);
    reportNotify(e.message || 'Error al exportar PDF', 'danger');
  } finally {
    setExportBusy(btns, false);
  }
}

let reportesAiState = {
  context: 'simple',
  scope: 'simple',
  catalog: { simples: [], compuestos: [], counts: null },
  lastGenerated: null,
  ai: null,
};

function reportesAiScopeLabel(scope) {
  return scope === 'compuesto' ? 'Compuesto · estratégico' : 'Simple · operativo';
}

function updateReportesAiScopeUi() {
  const scope = reportesAiState.scope;
  document.querySelectorAll('.reportes-ai-scope-pill').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.scope === scope);
  });
  const title = document.getElementById('reportes-ai-title');
  const sub = document.getElementById('reportes-ai-sub');
  const genPrompt = document.getElementById('reportes-ai-gen-prompt');
  if (title) {
    title.textContent = scope === 'compuesto' ? 'Asistente IA — informes estratégicos' : 'Asistente IA — informes operativos';
  }
  if (sub) {
    sub.textContent = scope === 'compuesto'
      ? 'Recomienda y genera análisis estratégicos (RC): ventas agregadas, rankings, márgenes y KPIs.'
      : 'Recomienda y genera listados operativos (RS): pedidos, stock, soporte y proveedores.';
  }
  if (genPrompt) {
    genPrompt.placeholder = scope === 'compuesto'
      ? 'Ej.: Ventas por mes y categoría, top productos, margen por categoría…'
      : 'Ej.: Productos con poco stock, pedidos pendientes de pago, chats sin responder…';
  }
  const recPrompt = document.getElementById('reportes-ai-rec-prompt');
  if (recPrompt) {
    recPrompt.placeholder = scope === 'compuesto'
      ? 'Ej.: tendencia de ventas, ranking, rotación de inventario…'
      : 'Ej.: stock bajo, pagos pendientes, órdenes de compra abiertas…';
  }
}

function setReportesAiScope(scope) {
  reportesAiState.scope = scope === 'compuesto' ? 'compuesto' : 'simple';
  updateReportesAiScopeUi();
  loadReportesAiRecommendations();
}

async function refreshReportesAiCatalog(notifyUser) {
  const meta = document.getElementById('reportes-ai-catalog-meta');
  const btn = document.getElementById('reportes-ai-refresh-catalog');
  if (btn) btn.disabled = true;
  if (meta) meta.textContent = 'Actualizando catálogo de informes…';
  try {
    const [rSimple, rComp] = await Promise.all([
      fetch(`${reportesApiBase()}/reportes`, { credentials: 'same-origin' }),
      fetch(`${reportesApiBase()}/compuestos`, { credentials: 'same-origin' }),
    ]);
    const dataSimple = await rSimple.json().catch(() => ({}));
    const dataComp = await rComp.json().catch(() => ({}));
    if (rSimple.ok && Array.isArray(dataSimple.reports)) {
      reportesCatalog = dataSimple.reports;
      const sel = document.getElementById('reportes-select');
      const prev = sel?.value;
      fillSelectOptions(sel, reportesCatalog);
      if (prev && reportesCatalog.some((x) => x.id === prev) && sel) sel.value = prev;
    }
    if (rComp.ok && Array.isArray(dataComp.reports)) {
      rcUsingFallback = false;
      rcCatalog = dataComp.reports;
      setRcFallbackBanner(false);
      const sel = document.getElementById('rc-select');
      const prev = sel?.value;
      fillSelectOptions(sel, rcCatalog);
      if (prev && rcCatalog.some((x) => x.id === prev) && sel) sel.value = prev;
    }
    const rCat = await fetch(
      `${reportesApiBase()}/reportes/ia/catalogo?scope=${encodeURIComponent(reportesAiState.scope)}`,
      { credentials: 'same-origin' }
    );
    const cat = await rCat.json().catch(() => ({}));
    if (rCat.ok) {
      reportesAiState.catalog.counts = cat.counts || null;
      reportesAiState.ai = cat.ai || null;
      if (meta && cat.counts) {
        const aiText = cat.ai?.ai_available
          ? `API configurada · ${cat.ai.provider || 'OpenAI'} · ${cat.ai.model || 'modelo configurado'}`
          : 'API pendiente de configurar';
        meta.textContent = `Catálogo: ${cat.counts.simples} simples (RS) · ${cat.counts.compuestos} compuestos (RC) · ${cat.counts.scoped} en este tipo · ${aiText}`;
      }
      const engine = document.getElementById('reportes-ai-engine');
      if (engine) {
        engine.textContent = cat.ai?.engine_note || '';
        engine.classList.toggle('reportes-ai-engine--error', !cat.ai?.ai_available);
      }
      ['reportes-ai-rec-btn', 'reportes-ai-gen-btn'].forEach((id) => {
        const action = document.getElementById(id);
        if (action) action.disabled = !cat.ai?.ai_available;
      });
    } else if (meta) {
      meta.textContent = `Catálogo: ${reportesCatalog.length} simples · ${rcCatalog.length} compuestos`;
    }
    if (notifyUser) reportNotify('Tipos de informe actualizados', 'ok');
  } catch (e) {
    if (meta) meta.textContent = e.message || 'No se pudo actualizar el catálogo';
    if (notifyUser) reportNotify(e.message || 'Error al actualizar catálogo', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function switchReportesAiTab(tab) {
  document.querySelectorAll('.reportes-ai-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  const rec = document.getElementById('reportes-ai-panel-recomendar');
  const gen = document.getElementById('reportes-ai-panel-generar');
  if (rec) rec.hidden = tab !== 'recomendar';
  if (gen) gen.hidden = tab !== 'generar';
}

function openReportesAiModal(context) {
  reportesAiState.context = context === 'compuesto' ? 'compuesto' : 'simple';
  reportesAiState.scope = reportesAiState.context;
  const modal = document.getElementById('reportes-ai-modal');
  if (!modal) return;
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  updateReportesAiScopeUi();
  switchReportesAiTab('recomendar');
  const genResult = document.getElementById('reportes-ai-gen-result');
  if (genResult) genResult.hidden = true;
  refreshReportesAiCatalog(false).then(() => {
    if (reportesAiState.ai?.ai_available) loadReportesAiRecommendations();
    else {
      const list = document.getElementById('reportes-ai-rec-list');
      if (list) list.innerHTML = '<div class="reportes-ai-api-required"><strong>Conecta la API para activar el asistente</strong><p>Agrega <code>OPENAI_API_KEY</code> en el archivo <code>.env</code> del servidor y reinicia la aplicación. La clave nunca se guarda en el navegador.</p></div>';
    }
  });
}

function closeReportesAiModal() {
  const modal = document.getElementById('reportes-ai-modal');
  if (!modal) return;
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
}

function renderReportGridTo(headEl, bodyEl, columns, rows, labels, emptyMsg) {
  const cols = columns || [];
  const labelMap = labels || REPORT_LABELS;
  if (!headEl || !bodyEl) return;
  headEl.innerHTML = `<tr>${cols.map((c) => `<th>${labelMap[c] || c}</th>`).join('')}</tr>`;
  if (!rows || !rows.length) {
    bodyEl.innerHTML = emptyTableHtml(cols.length || 1, emptyMsg || 'Sin datos.');
    return;
  }
  bodyEl.innerHTML = rows
    .map((row) => {
      const tds = cols
        .map((c) => {
          let v = row[c];
          if (typeof v === 'boolean') v = v ? 'Sí' : 'No';
          return `<td>${v == null || v === '' ? '—' : String(v)}</td>`;
        })
        .join('');
      return `<tr>${tds}</tr>`;
    })
    .join('');
}

async function loadReportesAiRecommendations() {
  const prompt = document.getElementById('reportes-ai-rec-prompt')?.value?.trim() || '';
  const list = document.getElementById('reportes-ai-rec-list');
  const engineEl = document.getElementById('reportes-ai-engine');
  const btn = document.getElementById('reportes-ai-rec-btn');
  if (!list) return;
  if (btn) btn.disabled = true;
  list.innerHTML = '<p class="catalog-meta">Analizando catálogo…</p>';
  try {
    const r = await fetch(`${reportesApiBase()}/reportes/ia/recomendar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt || null,
        limit: 5,
        scope: reportesAiState.scope,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.message || 'No se pudieron obtener recomendaciones.');
    const engine = data.engine === 'openai' ? 'Motor: OpenAI Responses API' : 'Motor no disponible';
    if (engineEl) {
      const counts = data.catalog_counts;
      const countTxt = counts ? ` · ${counts.scoped} informes en este tipo` : '';
      const note = data.engine_note || '';
      engineEl.textContent = `${engine} · ${reportesAiScopeLabel(reportesAiState.scope)}${countTxt}${note ? ' — ' + note : ''}`;
    }
    const recs = data.recommendations || [];
    if (!recs.length) {
      list.innerHTML = '<p class="catalog-meta">No hay recomendaciones para esa consulta.</p>';
      return;
    }
    list.innerHTML = recs
      .map(
        (rec) => {
          const tipoBadge = rec.tipo_label || reportesAiScopeLabel(rec.tipo || 'simple');
          return `<article class="reportes-ai-rec-card">
          <h4>${reportHtml(rec.report_id)} — ${reportHtml(rec.name || '')}</h4>
          <p>${reportHtml(rec.para_que || '')}</p>
          ${rec.reason ? `<p class="reportes-ai-rec-reason"><strong>Por qué lo recomienda:</strong> ${reportHtml(rec.reason)}</p>` : ''}
          <div class="reportes-ai-rec-actions">
            <span class="reportes-ai-badge reportes-ai-badge--tipo">${reportHtml(tipoBadge)}</span>
            <span class="reportes-ai-badge">${reportHtml(rec.confidence || 'media')}</span>
            <button type="button" class="btn btn-primary btn-sm" onclick="openAiRecommendedReport('${reportHtml(rec.report_id)}', '${reportHtml(rec.tipo || 'simple')}')">Abrir informe</button>
          </div>
        </article>`;
        }
      )
      .join('');
  } catch (e) {
    list.innerHTML = `<p class="catalog-meta">${e.message || 'Error al recomendar'}</p>`;
    reportNotify(e.message || 'Error al recomendar', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function generateReportesAiCustom() {
  const prompt = document.getElementById('reportes-ai-gen-prompt')?.value?.trim();
  const btn = document.getElementById('reportes-ai-gen-btn');
  const result = document.getElementById('reportes-ai-gen-result');
  if (!prompt) {
    reportNotify('Describe el informe que necesitas.', 'warn');
    return;
  }
  if (btn) btn.disabled = true;
  if (result) result.hidden = true;
  reportNotify('Generando informe…', 'info');
  try {
    const thr = document.getElementById('reportes-thr')?.value || '20';
    const r = await fetch(`${reportesApiBase()}/reportes/ia/generar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        limit: 120,
        threshold: parseInt(thr, 10) || 20,
        scope: reportesAiState.scope,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.message || 'No se pudo generar el informe.');
    reportesAiState.lastGenerated = data;
    const narrative = document.getElementById('reportes-ai-gen-narrative');
    const meta = document.getElementById('reportes-ai-gen-meta');
    if (narrative) narrative.textContent = data.narrative || '';
    if (meta) {
      const tipoTxt = data.tipo_label || reportesAiScopeLabel(data.tipo || reportesAiState.scope);
      meta.textContent = `${data.report?.name || 'Informe'} · ${tipoTxt} · base ${data.matched_report_id || ''} · ${data.total ?? 0} fila(s) · ${data.engine === 'openai' ? 'IA' : 'local'}`;
    }
    const cols = (data.report && data.report.columns) || [];
    const labels = data.tipo === 'compuesto' ? RC_LABELS : REPORT_LABELS;
    renderReportGridTo(
      document.getElementById('reportes-ai-gen-head'),
      document.getElementById('reportes-ai-gen-body'),
      cols,
      data.rows || [],
      labels,
      data.message || 'Sin datos para este informe.'
    );
    if (result) result.hidden = false;
    reportNotify('Informe generado', 'ok');
  } catch (e) {
    reportNotify(e.message || 'Error al generar', 'danger');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openAiRecommendedReport(reportId, tipo) {
  closeReportesAiModal();
  if (tipo === 'compuesto') {
    openStrategicReport(reportId);
    return;
  }
  if (typeof showPage === 'function') showPage('reportes');
  const sel = document.getElementById('reportes-select');
  if (sel) {
    sel.value = reportId;
    if (typeof onReportesSelect === 'function') onReportesSelect();
    if (typeof loadReporteActual === 'function') loadReporteActual();
  }
}

function applyReportesAiResult() {
  const data = reportesAiState.lastGenerated;
  if (!data) return;
  closeReportesAiModal();
  const tipo = data.tipo || (data.report?.tipo === 'compuesto' ? 'compuesto' : 'simple');
  const rid = data.matched_report_id || data.report?.source_report_id;
  if (tipo === 'compuesto') {
    if (typeof showPage === 'function') showPage('reportes-compuestos');
    const sel = document.getElementById('rc-select');
    const head = document.getElementById('rc-head');
    const body = document.getElementById('rc-body');
    const count = document.getElementById('rc-count');
    const title = document.getElementById('rc-title');
    const meta = document.getElementById('rc-meta');
    if (sel && rid) sel.value = rid;
    if (title && data.report) title.textContent = data.report.name || title.textContent;
    if (meta && data.report) setReportMeta(meta, data.report);
    const cols = data.report?.columns || [];
    lastRcGrid = { id: rid || '', columns: cols, rows: data.rows || [], labels: RC_LABELS };
    renderReportGridTo(head, body, cols, data.rows, RC_LABELS, data.message);
    if (count) count.textContent = `${data.total ?? (data.rows || []).length} fila(s)`;
    if (typeof onRcSelect === 'function') onRcSelect();
    return;
  }
  if (typeof showPage === 'function') showPage('reportes');
  const sel = document.getElementById('reportes-select');
  const head = document.getElementById('reportes-head');
  const body = document.getElementById('reportes-body');
  const count = document.getElementById('reportes-count');
  const title = document.getElementById('reportes-title');
  const meta = document.getElementById('reportes-meta');
  if (sel && rid) sel.value = rid;
  const qInput = document.getElementById('reportes-q');
  if (qInput && data.search_query) qInput.value = data.search_query;
  if (title && data.report) title.textContent = data.report.name || title.textContent;
  if (meta && data.report) setReportMeta(meta, data.report);
  const cols = data.report?.columns || [];
  lastReporteGrid = { id: rid || '', columns: cols, rows: data.rows || [], labels: REPORT_LABELS };
  renderReportGridTo(head, body, cols, data.rows, REPORT_LABELS, data.message);
  if (count) count.textContent = `${data.total ?? (data.rows || []).length} fila(s)`;
  if (typeof onReportesSelect === 'function') onReportesSelect();
}

window.loadReportesPage = loadReportesPage;
window.onReportesSelect = onReportesSelect;
window.loadReporteActual = loadReporteActual;
window.loadRcPage = loadRcPage;
window.onRcSelect = onRcSelect;
window.loadRcActual = loadRcActual;
window.openStrategicReport = openStrategicReport;
window.exportReportePdf = exportReportePdf;
window.exportRcPdf = exportRcPdf;
window.exportReporteCsv = exportReporteCsv;
window.exportRcCsv = exportRcCsv;
window.openReportesAiModal = openReportesAiModal;
window.closeReportesAiModal = closeReportesAiModal;
window.switchReportesAiTab = switchReportesAiTab;
window.loadReportesAiRecommendations = loadReportesAiRecommendations;
window.generateReportesAiCustom = generateReportesAiCustom;
window.openAiRecommendedReport = openAiRecommendedReport;
window.applyReportesAiResult = applyReportesAiResult;
window.setReportesAiScope = setReportesAiScope;
window.refreshReportesAiCatalog = refreshReportesAiCatalog;
window.clearReportesFilters = clearReportesFilters;
window.clearRcFilters = clearRcFilters;
