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

function reportesApiBase() {
  if (typeof API === 'string' && API) return API;
  if (typeof window !== 'undefined' && window.API) return window.API;
  return (window.location.origin || '') + '/api';
}

let reportesCatalog = [];
let rcCatalog = [];

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
    sel.innerHTML = reportesCatalog
      .map((rep) => `<option value="${rep.id}">${rep.name || rep.id}</option>`)
      .join('');
    if (!reportesCatalog.length) {
      if (meta) meta.textContent = 'No hay informes disponibles.';
      return;
    }
    if (prev && reportesCatalog.some((x) => x.id === prev)) sel.value = prev;
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
  if (meta) {
    meta.textContent = rep?.para_que || '';
  }
}

async function loadReporteActual() {
  const id = document.getElementById('reportes-select')?.value;
  const body = document.getElementById('reportes-body');
  const head = document.getElementById('reportes-head');
  const count = document.getElementById('reportes-count');
  if (!id || !body || !head) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const q = document.getElementById('reportes-q')?.value || '';
  const thr = document.getElementById('reportes-thr')?.value || '20';
  let url = `${reportesApiBase()}/reportes/${encodeURIComponent(id)}?limit=200`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (id === 'RS-03') url += `&threshold=${encodeURIComponent(thr)}`;
  try {
    const r = await fetch(url, { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      body.innerHTML = `<tr><td colspan="8">${data.message || 'No se pudo cargar el informe.'}</td></tr>`;
      return;
    }
    const cols = (data.report && data.report.columns) || data.columns || [];
    const rows = data.rows || [];
    head.innerHTML = `<tr>${cols.map((c) => `<th>${REPORT_LABELS[c] || c}</th>`).join('')}</tr>`;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="${cols.length || 1}">Sin datos para este informe.</td></tr>`;
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
    body.innerHTML = `<tr><td colspan="8">${e.message || 'Error'}</td></tr>`;
  }
}

async function loadRcPage() {
  const sel = document.getElementById('rc-select');
  const meta = document.getElementById('rc-meta');
  if (!sel) return;
  try {
    const r = await fetch(reportesApiBase() + '/reportes/compuestos', { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (meta) meta.textContent = data.message || 'No se pudieron cargar los informes.';
      sel.innerHTML = '';
      return;
    }
    rcCatalog = data.reports || [];
    const prev = sel.value;
    sel.innerHTML = rcCatalog
      .map((rep) => `<option value="${rep.id}">${rep.name || rep.id}</option>`)
      .join('');
    if (!rcCatalog.length) {
      if (meta) meta.textContent = 'No hay informes disponibles.';
      return;
    }
    if (prev && rcCatalog.some((x) => x.id === prev)) sel.value = prev;
    else sel.selectedIndex = 0;
    onRcSelect();
    await loadRcActual();
  } catch (e) {
    if (meta) meta.textContent = e.message || 'Error al cargar informes';
  }
}

function onRcSelect() {
  const id = document.getElementById('rc-select')?.value;
  const rep = rcCatalog.find((x) => x.id === id);
  const title = document.getElementById('rc-title');
  const meta = document.getElementById('rc-meta');
  if (title) title.textContent = rep ? rep.name : 'Informe';
  if (meta) meta.textContent = rep?.para_que || '';
}

async function loadRcActual() {
  const id = document.getElementById('rc-select')?.value;
  const body = document.getElementById('rc-body');
  const head = document.getElementById('rc-head');
  const count = document.getElementById('rc-count');
  const meta = document.getElementById('rc-meta');
  if (!body || !head) return;
  if (!id) {
    body.innerHTML = '<tr><td colspan="8">Elige un informe en la lista.</td></tr>';
    return;
  }
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  try {
    const r = await fetch(`${reportesApiBase()}/reportes/compuestos/${encodeURIComponent(id)}?limit=120`, {
      credentials: 'same-origin',
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      body.innerHTML = `<tr><td colspan="8">${data.message || 'No se pudo cargar el informe.'}</td></tr>`;
      if (meta && data.message) meta.textContent = data.message;
      return;
    }
    const cols = (data.report && data.report.columns) || [];
    const rows = data.rows || [];
    head.innerHTML = `<tr>${cols.map((c) => `<th>${RC_LABELS[c] || c}</th>`).join('')}</tr>`;
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="${cols.length || 1}">Sin datos para este informe.</td></tr>`;
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
    body.innerHTML = `<tr><td colspan="8">${e.message || 'Error'}</td></tr>`;
  }
}

window.loadReportesPage = loadReportesPage;
window.onReportesSelect = onReportesSelect;
window.loadReporteActual = loadReporteActual;
window.loadRcPage = loadRcPage;
window.onRcSelect = onRcSelect;
window.loadRcActual = loadRcActual;
