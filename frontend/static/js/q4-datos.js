/* Q4 Datos — maestras CRUD */
let datosState = { table: '', rows: [], total: 0, offset: 0, limit: 50 };

const MASTER_PK = {
  dim_region: 'region_id',
  dim_pais: 'country_id',
  dim_categoria: 'category_id',
  dim_producto: 'product_id',
  dim_canal: 'channel_id',
  dim_prioridad: 'priority_id',
  dim_cliente: 'client_id',
  dim_tiempo: 'tiempo_id',
};

function masterPk(row) {
  const k = MASTER_PK[datosState.table];
  return k ? row[k] : null;
}

async function loadDatosPage() {
  await loadMasterTablesList();
  if (!datosState.table) {
    const sel = document.getElementById('datos-table-select');
    if (sel) {
      const preferred = Array.from(sel.options).find(o => o.value === 'dim_producto');
      if (preferred) {
        sel.value = 'dim_producto';
        datosState.table = 'dim_producto';
      } else if (sel.options.length > 1) {
        sel.selectedIndex = 1;
        datosState.table = sel.value;
      }
    }
  }
  if (datosState.table) await loadMasterRows();
}

async function loadMasterTablesList() {
  const sel = document.getElementById('datos-table-select');
  if (!sel) return;
  try {
    const r = await fetch(API + '/master/tables', { credentials: 'same-origin' });
    const data = await r.json();
    const tables = data.tables || [];
    const masters = tables.filter(t => t.group === 'maestros' || !t.group);
    const shop = tables.filter(t => t.group === 'comercio');
    const opt = (t) => `<option value="${t.name}">${t.label} · ${t.name} (${t.count})</option>`;
    sel.innerHTML = '<option value="">— Elegir tabla —</option>' +
      (masters.length ? `<optgroup label="Maestros DW">${masters.map(opt).join('')}</optgroup>` : '') +
      (shop.length ? `<optgroup label="Comercio Shopify">${shop.map(opt).join('')}</optgroup>` : '');
    if (datosState.table) sel.value = datosState.table;
  } catch (e) {
    sel.innerHTML = '<option>Error al cargar</option>';
  }
}

async function onDatosTableChange() {
  datosState.table = document.getElementById('datos-table-select').value;
  datosState.offset = 0;
  await loadMasterRows();
}

async function loadMasterRows() {
  const table = datosState.table;
  const body = document.getElementById('datos-rows-body');
  const meta = document.getElementById('datos-rows-meta');
  if (!table || !body) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const q = new URLSearchParams({ limit: datosState.limit, offset: datosState.offset });
  const r = await fetch(API + '/master/' + encodeURIComponent(table) + '?' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="8">${data.message || 'Error'}</td></tr>`;
    return;
  }
  datosState.rows = data.rows || [];
  datosState.total = data.total || 0;
  datosState.editable = data.editable === true;
  if (meta) meta.textContent = `${data.total} registros · ${data.label}${!datosState.editable ? ' (solo lectura)' : ''}`;
  if (!datosState.rows.length) {
    body.innerHTML = '<tr><td colspan="8">Sin registros</td></tr>';
    return;
  }
  const keys = Object.keys(datosState.rows[0]);
  document.getElementById('datos-rows-head').innerHTML =
    keys.map(k => `<th>${k}</th>`).join('') + '<th>Acciones</th>';
  body.innerHTML = datosState.rows.map(row => {
    const pk = masterPk(row) ?? row[keys[0]];
    const img = row.image_url || row.src ? `<br><img src="${row.image_url || row.src}" alt="" style="max-height:40px;margin-top:4px">` : '';
    const actions = datosState.editable
      ? `<button type="button" class="btn btn-ghost" style="padding:4px 8px;font-size:11px" onclick="openMasterEdit('${pk}')">Editar</button>
        <button type="button" class="btn btn-ghost" style="padding:4px 8px;font-size:11px" onclick="deleteMasterRow('${pk}')" ${!isAdmin() ? 'disabled' : ''}>Eliminar</button>`
      : '<span style="font-size:11px;color:var(--muted)">Sync Shopify</span>';
    return `<tr>${keys.map(k => `<td>${formatCell(row[k])}${k === 'name' || k === 'title' ? img : ''}</td>`).join('')}
      <td style="white-space:nowrap">${actions}</td></tr>`;
  }).join('');
}

function formatCell(v) {
  if (v == null) return '—';
  if (typeof v === 'number') return Number(v).toLocaleString('es-EC');
  return String(v);
}

function isAdmin() {
  return window._authUser && window._authUser.role === 'administrador';
}

function openMasterCreate() {
  if (!isAdmin()) { alert('Solo administradores.'); return; }
  if (datosState.editable === false) { alert('Tabla comercial: usa Sync Shopify o edita maestros dim_*.'); return; }
  document.getElementById('master-form-title').textContent = 'Nuevo registro';
  document.getElementById('master-form-pk').value = '';
  document.getElementById('master-form-fields').innerHTML = buildMasterFormFields({});
  document.getElementById('master-image-block').hidden = datosState.table !== 'dim_producto';
  document.getElementById('master-form-modal').hidden = false;
}

function openMasterEdit(pk) {
  if (!isAdmin()) { alert('Solo administradores.'); return; }
  const found = datosState.rows.find(r => String(masterPk(r)) === String(pk));
  if (!found) return;
  document.getElementById('master-form-title').textContent = 'Editar registro';
  document.getElementById('master-form-pk').value = pk;
  document.getElementById('master-form-fields').innerHTML = buildMasterFormFields(found);
  document.getElementById('master-image-block').hidden = datosState.table !== 'dim_producto';
  document.getElementById('master-form-modal').hidden = false;
}

function buildMasterFormFields(row) {
  const samples = {
    dim_region: ['name', 'description'],
    dim_pais: ['name', 'region_id'],
    dim_categoria: ['name', 'description'],
    dim_producto: ['name', 'category_id', 'line', 'unit_price', 'unit_cost'],
    dim_canal: ['name', 'description'],
    dim_prioridad: ['code', 'name', 'sla_days', 'description'],
    dim_cliente: ['name', 'country_id', 'channel_id', 'email', 'phone'],
  };
  const fields = samples[datosState.table] || ['name'];
  return fields.map(f => `
    <div class="fg"><label>${f}</label>
    <input id="mf-${f}" type="text" value="${row[f] != null ? row[f] : ''}" /></div>`).join('');
}

function closeMasterForm() {
  document.getElementById('master-form-modal').hidden = true;
}

async function saveMasterForm() {
  const table = datosState.table;
  const pk = document.getElementById('master-form-pk').value;
  const samples = {
    dim_region: ['name', 'description'],
    dim_pais: ['name', 'region_id'],
    dim_categoria: ['name', 'description'],
    dim_producto: ['name', 'category_id', 'line', 'unit_price', 'unit_cost'],
    dim_canal: ['name', 'description'],
    dim_prioridad: ['code', 'name', 'sla_days', 'description'],
    dim_cliente: ['name', 'country_id', 'channel_id', 'email', 'phone'],
  };
  const body = {};
  (samples[table] || []).forEach(f => {
    const el = document.getElementById('mf-' + f);
    if (!el) return;
    let v = el.value.trim();
    if (['region_id', 'country_id', 'category_id', 'channel_id', 'priority_id', 'client_id', 'line', 'sla_days', 'product_id'].includes(f) ||
        f.endsWith('_id')) {
      v = v === '' ? null : Number(v);
    }
    if (f === 'unit_price' || f === 'unit_cost') v = parseFloat(v) || 0;
    body[f] = v;
  });
  const url = pk ? `${API}/master/${table}/${pk}` : `${API}/master/${table}`;
  const r = await fetch(url, {
    method: pk ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  if (table === 'dim_producto') {
    const file = document.getElementById('master-image-file');
    const prodId = pk || data.row?.product_id;
    if (file && file.files[0] && prodId) await uploadProductImage(prodId, file.files[0]);
  }
  closeMasterForm();
  await loadMasterRows();
  await loadMasterTablesList();
}

async function uploadProductImage(productId, file) {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(`${API}/master/dim_producto/${productId}/image`, {
    method: 'POST', credentials: 'same-origin', body: fd,
  });
  const data = await r.json();
  if (!r.ok) alert(data.message || 'Error al subir imagen');
}

async function deleteMasterRow(pk) {
  if (!isAdmin() || !confirm('¿Eliminar registro?')) return;
  const r = await fetch(`${API}/master/${datosState.table}/${pk}`, {
    method: 'DELETE', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  await loadMasterRows();
  await loadMasterTablesList();
}

async function runBuildModel() {
  if (!isAdmin()) { alert('Solo administradores.'); return; }
  const st = document.getElementById('datos-build-status');
  st.textContent = 'Reconstruyendo modelo…';
  const r = await fetch(API + '/build_model', { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  st.textContent = r.ok
    ? `✓ fact_ventas: ${data.fact_ventas?.toLocaleString()} · dim_producto: ${data.dim_producto}`
    : '✗ ' + (data.message || 'Error');
}

async function loadDatosEltPage() {
  const el = document.getElementById('elt-status-box');
  if (!el) return;
  try {
    const r = await fetch(API + '/elt_status');
    const d = await r.json();
    const c = d.counts || {};
    el.innerHTML = `
      <p><strong>MongoDB:</strong> ${d.mongo_db || '—'}</p>
      <p><strong>CSV:</strong> ${d.csv_exists ? '✓' : '✗'} ${d.csv_source || ''}</p>
      <p><strong>Parquet:</strong> ${d.parquet_exists ? '✓' : '✗'}</p>
      <p style="font-family:var(--mono);font-size:11px;margin-top:8px">
        sales_records: ${c.sales_records ?? '—'} · fact_ventas: ${c.fact_ventas ?? '—'} ·
        dim_producto: ${c.dim_producto ?? '—'} · solicitudes: ${c.purchase_requests ?? '—'}
      </p>`;
  } catch (e) {
    el.textContent = 'Error al consultar estado ELT';
  }
}

async function runShopSync() {
  if (!isAdmin()) { alert('Solo administradores.'); return; }
  const st = document.getElementById('datos-build-status');
  if (st) st.textContent = 'Sincronizando catálogo Shopify desde maestros…';
  try {
    const r = await fetch(API + '/shop/sync', { method: 'POST', credentials: 'same-origin' });
    const d = await r.json();
    if (!r.ok) {
      if (st) st.textContent = '✗ ' + (d.message || 'Error al sincronizar');
      alert(d.message || 'Error al sincronizar catálogo Shopify');
      return;
    }
    if (st) st.textContent = '✓ ' + (d.message || 'Sincronizado') + (d.counts ? ' · ' + Object.entries(d.counts).slice(0, 4).map(([k, v]) => `${k}: ${v}`).join(', ') : '');
    await loadMasterTablesList();
    if (datosState.table) await loadMasterRows();
  } catch (e) {
    if (st) st.textContent = 'Error: ' + e.message;
  }
}

async function loadDatasetQ4() {
  if (!isAdmin()) { alert('Solo administradores.'); return; }
  const log = document.getElementById('load-log');
  const btn = document.getElementById('btn-load');
  if (!log) return;
  btn.disabled = true;
  log.textContent = 'Iniciando carga ELT…\n';
  try {
    const r = await fetch(API + '/load_dataset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ csv_path: document.getElementById('csv-path')?.value || 'data/sales.csv' }),
    });
    const d = await r.json();
    log.textContent += (d.status === 'ok' ? '✓ ' : '✗ ') + (d.message || JSON.stringify(d)) + '\n';
    if (d.status === 'ok') loadDatosEltPage();
  } catch (e) {
    log.textContent += '✗ ' + e.message + '\n';
  }
  btn.disabled = false;
  if (btn) btn.textContent = '⬆ Cargar dataset completo';
}

async function loadAuditPage() {
  const body = document.getElementById('audit-body');
  if (!body) return;
  if (!window._authUser) {
    body.innerHTML = '<tr><td colspan="5">Inicia sesión para ver auditoría.</td></tr>';
    return;
  }
  const r = await fetch(API + '/audit_log?limit=50', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="5">${data.message || 'Error al cargar auditoría'}</td></tr>`;
    return;
  }
  const rows = data.entries || [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5">Sin registros de auditoría.</td></tr>';
    return;
  }
  body.innerHTML = rows.map(e => `
    <tr>
      <td style="font-size:11px">${e.at || '—'}</td>
      <td>${e.action || '—'}</td>
      <td>${e.entity || '—'}</td>
      <td>${e.email || '—'}</td>
      <td style="font-size:10px;color:var(--muted)">${e.entity_id ?? ''}</td>
    </tr>`).join('');
}
