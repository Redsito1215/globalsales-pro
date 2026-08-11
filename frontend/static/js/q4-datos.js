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
    const opt = (t) => `<option value="${t.name}">${t.label} · ${t.name} (${t.count})</option>`;
    sel.innerHTML = '<option value="">— Elegir tabla maestra —</option>' +
      tables.map(opt).join('');
    if (datosState.table) sel.value = datosState.table;
  } catch (e) {
    sel.innerHTML = '<option>Error al cargar</option>';
    notifyErr('No se pudo cargar la lista de tablas maestras.');
  }
}

async function onDatosTableChange() {
  datosState.table = document.getElementById('datos-table-select').value;
  datosState.offset = 0;
  if (!datosState.table) {
    const body = document.getElementById('datos-rows-body');
    const meta = document.getElementById('datos-rows-meta');
    const head = document.getElementById('datos-rows-head');
    if (head) head.innerHTML = '<tr><th>—</th></tr>';
    if (body) {
      body.innerHTML = typeof opsEmptyRow === 'function'
        ? opsEmptyRow(1, { title: 'Elige una tabla', hint: 'Selecciona una dimensión maestra del listado superior.' })
        : '<tr><td colspan="8">Elige una tabla maestra.</td></tr>';
    }
    if (meta) meta.textContent = '';
    return;
  }
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
    notifyErr(data.message || 'Error al cargar registros.');
    return;
  }
  datosState.rows = data.rows || [];
  datosState.total = data.total || 0;
  datosState.editable = data.editable === true;
  if (meta) meta.textContent = `${data.total} registros · ${data.label}${!datosState.editable ? ' (solo lectura)' : ''}`;
  if (!datosState.rows.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(8, {
          title: 'Sin registros',
          hint: canWriteMasters() ? 'Usa «+ Nuevo» para agregar el primero.' : 'Esta tabla aún no tiene filas.',
        })
      : '<tr><td colspan="8">Sin registros</td></tr>';
    if (document.getElementById('datos-rows-head')) {
      document.getElementById('datos-rows-head').innerHTML = '<tr><th>—</th></tr>';
    }
    return;
  }
  const keys = Object.keys(datosState.rows[0]);
  document.getElementById('datos-rows-head').innerHTML =
    keys.map(k => `<th>${k}</th>`).join('') + '<th>Acciones</th>';
  body.innerHTML = datosState.rows.map(row => {
    const pk = masterPk(row) ?? row[keys[0]];
    const img = row.image_url || row.src
      ? `<br><img class="master-thumb" src="${row.image_url || row.src}" alt="" />`
      : '';
    const actions = canWriteMasters()
      ? `<div class="master-actions table-actions">
          <button type="button" class="btn btn-ghost btn-sm" onclick="openMasterEdit('${pk}')">Editar</button>
          <button type="button" class="btn btn-ghost btn-sm" onclick="deleteMasterRow('${pk}')">Eliminar</button>
        </div>`
      : '<span class="master-note">Sin permiso de escritura</span>';
    return `<tr>${keys.map(k => `<td>${formatCell(row[k])}${k === 'name' || k === 'title' ? img : ''}</td>`).join('')}
      <td>${actions}</td></tr>`;
  }).join('');
}

function formatCell(v) {
  if (v == null) return '—';
  if (typeof v === 'number') return Number(v).toLocaleString('es-EC');
  return String(v);
}

function canWriteMasters() {
  return typeof hasPermission === 'function' && hasPermission('masters.write');
}

function canRunElt() {
  return typeof hasPermission === 'function' && hasPermission('elt.run');
}

function canReadAudit() {
  return typeof hasPermission === 'function' && hasPermission('audit.read');
}

function openMasterCreate() {
  if (!canWriteMasters()) { notifyErr('No tienes permiso para editar maestros.'); return; }
  if (!datosState.table) {
    notifyWarn('Elige primero una tabla maestra.');
    return;
  }
  if (datosState.editable === false) {
    notifyWarn('Esta tabla no admite edición manual desde aquí.');
    return;
  }
  document.getElementById('master-form-title').textContent = 'Nuevo registro';
  document.getElementById('master-form-pk').value = '';
  document.getElementById('master-form-fields').innerHTML = buildMasterFormFields({});
  document.getElementById('master-image-block').hidden = datosState.table !== 'dim_producto';
  document.getElementById('master-form-modal').hidden = false;
}

function openMasterEdit(pk) {
  if (!canWriteMasters()) { notifyErr('No tienes permiso para editar maestros.'); return; }
  const found = datosState.rows.find(r => String(masterPk(r)) === String(pk));
  if (!found) {
    notifyWarn('Registro no encontrado. Recarga la tabla.');
    return;
  }
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
  const intFields = new Set(['region_id', 'country_id', 'category_id', 'channel_id', 'line', 'sla_days', 'product_id']);
  const moneyFields = new Set(['unit_price', 'unit_cost']);
  return fields.map(f => {
    const inputType = intFields.has(f) || moneyFields.has(f) ? 'number' : 'text';
    const minAttr = intFields.has(f) ? ' min="1" step="1"' : (moneyFields.has(f) ? ' min="0.01" step="0.01"' : '');
    return `
    <div class="fg"><label>${f}</label>
    <input id="mf-${f}" type="${inputType}"${minAttr} value="${row[f] != null ? row[f] : ''}" /></div>`;
  }).join('');
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
  const intPositive = new Set(['region_id', 'country_id', 'category_id', 'channel_id', 'line', 'sla_days', 'product_id']);
  const floatPositive = new Set(['unit_price', 'unit_cost']);
  const body = {};
  for (const f of (samples[table] || [])) {
    const el = document.getElementById('mf-' + f);
    if (!el) continue;
    const raw = el.value.trim();
    if (intPositive.has(f) || f.endsWith('_id')) {
      if (!raw || !/^-?\d+$/.test(raw)) {
        notifyWarn(`«${f}» debe ser un número entero positivo.`);
        return;
      }
      const n = parseInt(raw, 10);
      if (n < 1) {
        notifyWarn(`«${f}» debe ser mayor a 0.`);
        return;
      }
      body[f] = n;
      continue;
    }
    if (floatPositive.has(f)) {
      if (!raw || Number.isNaN(Number(raw))) {
        notifyWarn(`«${f}» debe ser un número válido mayor a 0.`);
        return;
      }
      const n = parseFloat(raw);
      if (n <= 0) {
        notifyWarn(`«${f}» debe ser mayor a 0.`);
        return;
      }
      body[f] = n;
      continue;
    }
    if (f === 'name' && !raw) {
      notifyWarn('El nombre es obligatorio.');
      return;
    }
    body[f] = raw;
  }
  const url = pk ? `${API}/master/${table}/${pk}` : `${API}/master/${table}`;
  const r = await fetch(url, {
    method: pk ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error'); return; }
  if (table === 'dim_producto') {
    const file = document.getElementById('master-image-file');
    const prodId = pk || data.row?.product_id;
    if (file && file.files[0] && prodId) await uploadProductImage(prodId, file.files[0]);
  }
  closeMasterForm();
  await loadMasterRows();
  await loadMasterTablesList();
  notifyOk(pk ? 'Registro actualizado.' : 'Registro creado.');
}

async function uploadProductImage(productId, file) {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch(`${API}/master/dim_producto/${productId}/image`, {
    method: 'POST', credentials: 'same-origin', body: fd,
  });
  const data = await r.json();
  if (!r.ok) notifyErr(data.message || 'Error al subir imagen');
  else notifyOk('Imagen del producto actualizada.');
}

async function deleteMasterRow(pk) {
  if (!canWriteMasters()) {
    notifyErr('No tienes permiso para eliminar registros maestros.');
    return;
  }
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Eliminar registro',
    message: '¿Eliminar este registro de la tabla maestra? Esta acción no se puede deshacer.',
    confirmLabel: 'Eliminar',
    danger: true,
  });
  if (!ok) return;
  const r = await fetch(`${API}/master/${datosState.table}/${pk}`, {
    method: 'DELETE', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error'); return; }
  notifyOk('Registro eliminado.');
  await loadMasterRows();
  await loadMasterTablesList();
}

async function runBuildModel() {
  if (!canRunElt()) { notifyErr('No tienes permiso para reconstruir el modelo.'); return; }
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Reconstruir modelo',
    message: '¿Reconstruir fact_ventas y dimensiones desde sales_records? Puede tardar unos segundos.',
    confirmLabel: 'Reconstruir',
  });
  if (!ok) return;
  const st = document.getElementById('datos-build-status');
  st.textContent = 'Reconstruyendo modelo…';
  const r = await fetch(API + '/build_model', { method: 'POST', credentials: 'same-origin' });
  const data = await r.json();
  if (r.ok) {
    st.textContent = `✓ fact_ventas: ${data.fact_ventas?.toLocaleString()} · dim_producto: ${data.dim_producto}`;
    notifyOk('Modelo estratégico reconstruido.');
  } else {
    st.textContent = '✗ ' + (data.message || 'Error');
    notifyErr(data.message || 'Error al reconstruir el modelo');
  }
}

async function loadDatosEltPage() {
  const el = document.getElementById('elt-status-box');
  if (!el) return;
  try {
    const [r, metaR] = await Promise.all([
      fetch(API + '/elt_status'),
      fetch(API + '/meta/data-layers'),
    ]);
    const d = await r.json();
    const meta = metaR.ok ? await metaR.json() : {};
    const topo = meta.topology || {};
    const c = d.counts || {};
    const mongoLine = topo.split_enabled
      ? `<p><strong>MongoDB:</strong> ops <code>${topo.ops_database || '—'}</code> · DW <code>${topo.dw_database || '—'}</code></p>`
      : `<p><strong>MongoDB:</strong> ${d.mongo_db || topo.dw_database || '—'}</p>`;
    el.innerHTML = `
      ${mongoLine}
      <p><strong>CSV:</strong> ${d.csv_exists ? '✓' : '✗'} ${d.csv_source || ''}</p>
      <p><strong>Parquet:</strong> ${d.parquet_exists ? '✓' : '✗'}</p>
      <p style="font-family:var(--mono);font-size:11px;margin-top:8px">
        sales_records: ${c.sales_records ?? '—'} · fact_ventas: ${c.fact_ventas ?? '—'} ·
        dim_producto: ${c.dim_producto ?? '—'} · solicitudes: ${c.purchase_requests ?? '—'}
      </p>
      <p style="margin-top:8px;font-size:12px">
        Orquestación alternativa: DAG Airflow <code>globtrade_strategic_etl</code>
        (UI <a href="http://localhost:8080" target="_blank" rel="noopener">localhost:8080</a>) —
        rebuild truncate+reload para Informes compuestos RC / Tablero.
      </p>`;
  } catch (e) {
    el.textContent = 'Error al consultar estado ELT';
    notifyErr('No se pudo consultar el estado ELT.');
  }
}

async function runShopSync(resetStock = false) {
  if (!canWriteMasters()) { notifyErr('No tienes permiso para sincronizar el catálogo.'); return; }
  if (resetStock) {
    if (typeof opsConfirm !== 'function') {
      notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
      return;
    }
    const ok = await opsConfirm({
      title: 'Reiniciar stock',
      message: '¿Reiniciar stock desde maestros? Se perderán ajustes de inventario actuales.',
      confirmLabel: 'Reiniciar',
      danger: true,
    });
    if (!ok) return;
  }
  const st = document.getElementById('datos-build-status');
  if (st) st.textContent = resetStock
    ? 'Sincronizando catálogo y reiniciando stock…'
    : 'Sincronizando catálogo de tienda (conserva stock)…';
  try {
    const r = await fetch(API + '/shop/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ reset_stock: !!resetStock }),
    });
    const d = await r.json();
    if (!r.ok) {
      if (st) st.textContent = '✗ ' + (d.message || 'Error al sincronizar');
      notifyErr(d.message || 'Error al sincronizar catálogo de tienda');
      return;
    }
    if (st) st.textContent = '✓ ' + (d.message || 'Sincronizado') + (d.counts ? ' · ' + Object.entries(d.counts).slice(0, 4).map(([k, v]) => `${k}: ${v}`).join(', ') : '');
    notifyOk(d.message || 'Catálogo de tienda sincronizado.');
    await loadMasterTablesList();
    if (datosState.table) await loadMasterRows();
  } catch (e) {
    if (st) st.textContent = 'Error: ' + e.message;
    notifyErr(e.message || 'Error al sincronizar');
  }
}

async function loadDatasetQ4() {
  if (!canRunElt()) { notifyErr('No tienes permiso para ejecutar la carga ELT.'); return; }
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Carga ELT completa',
    message: '¿Truncar y recargar sales_records y reconstruir el modelo estratégico? Operación pesada (15–40 s).',
    confirmLabel: 'Iniciar carga',
    danger: true,
  });
  if (!ok) return;
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
    if (d.status === 'ok') {
      loadDatosEltPage();
      notifyOk(d.message || 'Carga ELT completada.');
    } else {
      notifyErr(d.message || 'Error en la carga ELT');
    }
  } catch (e) {
    log.textContent += '✗ ' + e.message + '\n';
    notifyErr(e.message || 'Error en la carga ELT');
  }
  btn.disabled = false;
  if (btn) btn.textContent = '⬆ Cargar dataset completo';
}

const AUDIT_PAGE_SIZE = 100;
let auditState = { page: 0, role: '' };

function auditGoPage(page) {
  auditState.page = Math.max(0, page);
  loadAuditPage();
}

function auditFormatAt(value) {
  const raw = String(value || '').trim();
  if (!raw) return '—';
  if (raw.length >= 19) return raw.slice(0, 19).replace('T', ' ');
  return raw;
}

function auditActionBadge(action) {
  const a = String(action || '').toLowerCase();
  let cls = 'badge badge--neutral audit-action';
  if (a.includes('delete') || a.includes('inhabilit') || a.includes('reject')) cls = 'badge badge--danger audit-action';
  else if (a.includes('create') || a.includes('habilit') || a.includes('approve')) cls = 'badge badge--ok audit-action';
  else if (a.includes('update') || a.includes('edit') || a.includes('patch')) cls = 'badge badge--info audit-action';
  return `<span class="${cls}">${action || '—'}</span>`;
}

async function loadAuditPage() {
  const body = document.getElementById('audit-body');
  const meta = document.getElementById('audit-meta');
  const pager = document.getElementById('audit-pager');
  const roleSel = document.getElementById('audit-role-filter');
  if (!body) return;
  const api = window.API || (window.location.origin + '/api');
  const cols = 6;
  if (!window._authUser) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(cols, { title: 'Sesión requerida', hint: 'Inicia sesión para consultar el registro de acciones.' })
      : `<tr><td colspan="${cols}">Inicia sesión para ver auditoría.</td></tr>`;
    if (meta) meta.textContent = '';
    if (pager) pager.hidden = true;
    return;
  }
  if (!canReadAudit()) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(cols, { title: 'Sin permiso', hint: 'Tu rol no puede ver auditoría.' })
      : `<tr><td colspan="${cols}">Tu rol no tiene permiso para ver auditoría.</td></tr>`;
    if (meta) meta.textContent = '';
    if (pager) pager.hidden = true;
    return;
  }
  if (roleSel) auditState.role = roleSel.value || '';
  body.innerHTML = `<tr><td colspan="${cols}">Cargando auditoría…</td></tr>`;
  if (meta) meta.textContent = 'Cargando…';
  if (pager) pager.innerHTML = '';
  const params = new URLSearchParams({
    limit: String(AUDIT_PAGE_SIZE),
    offset: String(auditState.page * AUDIT_PAGE_SIZE),
  });
  if (auditState.role) params.set('role', auditState.role);
  try {
    const r = await fetch(`${api}/audit_log?${params}`, { credentials: 'same-origin' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = data.message || data.error || `Error HTTP ${r.status}`;
      body.innerHTML = `<tr><td colspan="${cols}">${msg || 'Error al cargar auditoría'}</td></tr>`;
      if (meta) meta.textContent = '';
      return;
    }
    if (roleSel && Array.isArray(data.roles)) {
      const current = auditState.role;
      roleSel.innerHTML = `<option value="">Todos los roles</option>${data.roles.map(role =>
        `<option value="${role}" ${role === current ? 'selected' : ''}>${role}</option>`
      ).join('')}`;
    }
    const rows = data.entries || [];
    const total = Number(data.total) || 0;
    const offset = Number(data.offset) || 0;
    const limit = Number(data.limit) || AUDIT_PAGE_SIZE;
    const from = total ? offset + 1 : 0;
    const to = Math.min(offset + rows.length, total);
    const pages = Math.max(Math.ceil(total / limit), 1);
    if (auditState.page >= pages) {
      auditState.page = Math.max(pages - 1, 0);
      if (auditState.page !== Math.floor(offset / limit)) {
        await loadAuditPage();
        return;
      }
    }
    if (meta) {
      const roleLabel = auditState.role ? ` · rol ${auditState.role}` : '';
      meta.textContent = total
        ? `Mostrando ${from}–${to} de ${total} registros${roleLabel} · ${limit} por página`
        : 'Sin registros para este filtro';
    }
    if (!rows.length) {
      body.innerHTML = typeof opsEmptyRow === 'function'
        ? opsEmptyRow(cols, { title: 'Sin registros', hint: 'Prueba otro rol o vuelve más tarde.' })
        : `<tr><td colspan="${cols}">Sin registros de auditoría.</td></tr>`;
    } else {
      body.innerHTML = rows.map(e => `
    <tr>
      <td class="audit-cell-mono">${auditFormatAt(e.at)}</td>
      <td>${auditActionBadge(e.action)}</td>
      <td>${e.entity || '—'}</td>
      <td class="audit-cell-user">${e.email || '—'}</td>
      <td><code>${e.role || '—'}</code></td>
      <td class="audit-cell-id">${e.entity_id ?? '—'}</td>
    </tr>`).join('');
    }
    if (pager) {
      const page = auditState.page;
      const prevDisabled = page <= 0 ? 'disabled' : '';
      const nextDisabled = offset + limit >= total ? 'disabled' : '';
      pager.hidden = total <= limit && page <= 0;
      pager.innerHTML = `
        <button type="button" class="btn btn-ghost btn-sm" ${prevDisabled} onclick="auditGoPage(${page - 1})">← Anterior</button>
        <span class="table-pager-info">Página ${page + 1} de ${pages}</span>
        <button type="button" class="btn btn-ghost btn-sm" ${nextDisabled} onclick="auditGoPage(${page + 1})">Siguiente →</button>`;
    }
  } catch (e) {
    body.innerHTML = `<tr><td colspan="${cols}">Error al cargar auditoría: ${e.message || e}</td></tr>`;
    if (meta) meta.textContent = '';
    if (pager) pager.hidden = true;
  }
}

window.auditGoPage = auditGoPage;
window.loadAuditPage = loadAuditPage;
