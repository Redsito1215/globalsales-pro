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
  inventory_quantity: 'Stock',
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
  stock_actual: 'Stock actual',
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
  indicador: 'Indicador',
  valor: 'Valor',
  estado: 'Estado',
};

/** Catálogo local: el selector siempre tiene texto aunque falle el API de listado */
const RC_FALLBACK_CATALOG = [
  { id: 'RC-01', name: 'Ventas por mes y por categoría de producto', para_que: 'Ver cómo evolucionan las ventas por categoría en el tiempo.', quien: 'Gerente general, analista' },
  { id: 'RC-02', name: 'Top 10 productos que más se venden y top 10 que menos se venden', para_que: 'Comparar productos líderes y rezagados por ingresos.', quien: 'Gerente comercial, analista' },
  { id: 'RC-03', name: 'Balanza interna: cuánto se vendió frente a cuánto se compró', para_que: 'Comparar ventas frente a compras recibidas.', quien: 'Jefe de compras, gerencia' },
  { id: 'RC-04', name: 'Qué tan rápido rota el inventario por categoría', para_que: 'Cruzar unidades vendidas con stock actual.', quien: 'Jefe de inventario' },
  { id: 'RC-05', name: 'Tiempo promedio entre pedir y enviar, por país o región', para_que: 'Medir demora logística promedio por región.', quien: 'Jefe de logística' },
  { id: 'RC-06', name: 'Cuánto se usan los cupones y cómo afectan las ventas', para_que: 'Medir uso de cupones e impacto en ingresos.', quien: 'Gerente comercial' },
  { id: 'RC-07', name: 'Ganancia (margen) por categoría de producto en el tiempo', para_que: 'Ver margen % por categoría y mes.', quien: 'Gerente, analista' },
  { id: 'RC-08', name: 'Estado de la carga de datos para informes', para_que: 'Verificar si los datos de ventas están listos para análisis.', quien: 'Administrador, analista' },
];

let reportesCatalog = [];
let rcCatalog = [];
let rcUsingFallback = false;
let lastReporteGrid = { id: '', columns: [], rows: [], labels: REPORT_LABELS };
let lastRcGrid = { id: '', columns: [], rows: [], labels: RC_LABELS };

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

function fillSelectOptions(sel, catalog) {
  if (!sel) return;
  sel.innerHTML = (catalog || [])
    .map((rep) => `<option value="${rep.id}">${shortReportLabel(rep)}</option>`)
    .join('');
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
    body.innerHTML = emptyTableHtml(8, e.message || 'Error');
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
      const prev = sel.value;
      fillSelectOptions(sel, rcCatalog);
      if (prev && rcCatalog.some((x) => x.id === prev)) sel.value = prev;
      onRcSelect();
    } else {
      setRcFallbackBanner(true);
      if (!r.ok && meta) setReportMeta(meta, rcCatalog[0]);
    }
    await loadRcActual();
  } catch (e) {
    setRcFallbackBanner(true);
    if (meta) meta.textContent = e.message || 'Error al cargar informes';
    await loadRcActual();
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

async function loadRcActual() {
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
  lastRcGrid = { id, columns: [], rows: [], labels: RC_LABELS };
  try {
    const r = await fetch(`${reportesApiBase()}/compuestos/${encodeURIComponent(id)}?limit=120`, {
      credentials: 'same-origin',
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = data.message || 'No se pudo cargar el informe. Reinicia el servidor de la app e inténtalo de nuevo.';
      body.innerHTML = emptyTableHtml(8, msg, needsModelCta(id, msg));
      return;
    }
    const cols = (data.report && data.report.columns) || [];
    const rows = data.rows || [];
    lastRcGrid = { id, columns: cols, rows, labels: RC_LABELS };
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
    body.innerHTML = emptyTableHtml(8, e.message || 'Error', needsModelCta(id, e.message));
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

async function exportReportePdf() {
  const id = document.getElementById('reportes-select')?.value;
  if (!id) return;
  const q = document.getElementById('reportes-q')?.value || '';
  const thr = document.getElementById('reportes-thr')?.value || '20';
  let url = `${reportesApiBase()}/reportes/${encodeURIComponent(id)}/pdf?limit=500`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (id === 'RS-03') url += `&threshold=${encodeURIComponent(thr)}`;
  const btns = ['reportes-btn-pdf', 'reportes-btn-csv'];
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
  const url = `${reportesApiBase()}/compuestos/${encodeURIComponent(id)}/pdf?limit=500`;
  const btns = ['rc-btn-pdf', 'rc-btn-csv'];
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

function exportReporteCsv() {
  const grid = lastReporteGrid;
  if (!grid.id || !grid.columns.length) {
    reportNotify('Carga un informe antes de exportar CSV', 'danger');
    return;
  }
  if (!grid.rows.length) {
    reportNotify('No hay filas para exportar', 'danger');
    return;
  }
  downloadCsv(`globtrade-${grid.id}.csv`, grid.columns, grid.rows, grid.labels);
  setExportStatus('reportes-export-status', 'CSV descargado (vista actual).', true);
  reportNotify('CSV descargado', 'ok');
}

function exportRcCsv() {
  const grid = lastRcGrid;
  if (!grid.id || !grid.columns.length) {
    reportNotify('Carga un informe antes de exportar CSV', 'danger');
    return;
  }
  if (!grid.rows.length) {
    reportNotify('No hay filas para exportar', 'danger');
    return;
  }
  downloadCsv(`globtrade-${grid.id}.csv`, grid.columns, grid.rows, grid.labels);
  setExportStatus('rc-export-status', 'CSV descargado (vista actual).', true);
  reportNotify('CSV descargado', 'ok');
}

window.loadReportesPage = loadReportesPage;
window.onReportesSelect = onReportesSelect;
window.loadReporteActual = loadReporteActual;
window.loadRcPage = loadRcPage;
window.onRcSelect = onRcSelect;
window.loadRcActual = loadRcActual;
window.exportReportePdf = exportReportePdf;
window.exportRcPdf = exportRcPdf;
window.exportReporteCsv = exportReporteCsv;
window.exportRcCsv = exportRcCsv;
