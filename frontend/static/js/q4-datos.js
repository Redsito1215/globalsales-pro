/* Q4 Gestión — CRUD por entidad (listado + modal) */
let datosState = { table: 'dim_producto', rows: [], total: 0, offset: 0, limit: 10, search: '', activeFilter: '', categoryId: '', vendorId: '', fieldLabels: {}, columns: [], filterOptions: {} };
let gestionSearchTimer = null;
let gestionTablesCache = [];

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

function labelForField(key) {
  return datosState.fieldLabels?.[key] || key;
}

function showGestion(table, btn) {
  const tableName = table || 'dim_producto';
  datosState.table = tableName;
  datosState.offset = 0;
  datosState.search = '';
  datosState.categoryId = '';
  datosState.vendorId = '';
  const searchEl = document.getElementById('gestion-search');
  if (searchEl) searchEl.value = '';
  const categoryEl = document.getElementById('gestion-category');
  const vendorEl = document.getElementById('gestion-vendor');
  if (categoryEl) categoryEl.value = '';
  if (vendorEl) vendorEl.value = '';
  if (!canAccessPage('gestion')) {
    guardPageAccess('gestion');
    return;
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const page = document.getElementById('page-gestion');
  if (page) page.classList.add('active');
  const navBtn = btn || document.querySelector(`.nav-item[data-gestion-table="${tableName}"]`);
  if (navBtn) navBtn.classList.add('active');
  if (typeof openNavGroupForPage === 'function') openNavGroupForPage('gestion');
  const meta = gestionTablesCache.find(t => t.name === tableName);
  const title = meta?.label || tableName;
  const topbar = document.getElementById('topbar-title');
  if (topbar) topbar.textContent = title;
  loadGestionPage(true);
}

async function loadGestionPage(force) {
  await loadGestionTablesCache();
  updateGestionHeader();
  if (force || datosState.table) await loadMasterRows();
}

async function loadGestionTablesCache() {
  try {
    const r = await fetch(API + '/master/tables', { credentials: 'same-origin' });
    const data = await r.json();
    gestionTablesCache = data.tables || [];
  } catch (e) {
    gestionTablesCache = [];
  }
}

function updateGestionHeader() {
  const meta = gestionTablesCache.find(t => t.name === datosState.table);
  const titleEl = document.getElementById('gestion-title');
  const leadEl = document.getElementById('gestion-lead');
  if (titleEl) titleEl.textContent = meta?.label || datosState.table || 'Gestión';
  if (leadEl) {
    const base = meta?.description || 'Administra registros de esta dimensión.';
    leadEl.textContent = datosState.table === 'dim_producto'
      ? `${base} Activa una rebaja individual por producto (1–90%).`
      : datosState.table === 'dim_categoria'
        ? `${base} La rebaja de una categoría se aplica a todos sus productos activos.`
        : base;
  }
  const createBtn = document.getElementById('gestion-create-btn');
  if (createBtn) {
    const creatable = meta?.creatable !== false;
    createBtn.hidden = !creatable;
    createBtn.disabled = !creatable;
  }
  const productFiltersVisible = datosState.table === 'dim_producto';
  const categoryFilter = document.getElementById('gestion-category-filter');
  const vendorFilter = document.getElementById('gestion-vendor-filter');
  if (categoryFilter) categoryFilter.hidden = !productFiltersVisible;
  if (vendorFilter) vendorFilter.hidden = !productFiltersVisible;
}

function renderProductSaleToggle(row) {
  const pid = Number(row.product_id);
  const on = !!row.sale_enabled;
  const pct = Math.max(1, Math.min(90, Number(row.sale_percent) || 25));
  const disabled = canWriteMasters() ? '' : 'disabled';
  return `
    <div class="sale-toggle-wrap">
      <input type="number" class="sale-percent-input" min="1" max="90" step="1" value="${pct}" ${disabled}
        title="Porcentaje de rebaja" aria-label="Porcentaje de rebaja para ${String(row.name || pid).replace(/"/g, '&quot;')}"
        onchange="changeProductSalePercent(${pid}, this)" onclick="event.stopPropagation()" />
      <label class="sale-toggle sale-toggle--row ${on ? 'is-on' : ''}" title="Activar o desactivar rebaja">
        <input type="checkbox" class="sale-toggle-input" ${on ? 'checked' : ''} ${disabled}
          onchange="toggleProductSale(${pid}, this)" aria-label="Rebaja para ${String(row.name || pid).replace(/"/g, '&quot;')}" />
        <span class="sale-toggle-track" aria-hidden="true"><span class="sale-toggle-thumb"></span></span>
      </label>
    </div>`;
}

function renderCategorySaleToggle(row) {
  const cid = Number(row.category_id);
  const on = !!row.sale_enabled;
  const pct = Math.max(1, Math.min(90, Number(row.sale_percent) || 25));
  const disabled = canWriteMasters() ? '' : 'disabled';
  return `<div class="sale-toggle-wrap">
    <input type="number" class="sale-percent-input" min="1" max="90" step="1" value="${pct}" ${disabled}
      title="Porcentaje para toda la categoría" aria-label="Porcentaje de rebaja de la categoría"
      onchange="changeCategorySale(${cid}, this, false)" onclick="event.stopPropagation()" />
    <label class="sale-toggle sale-toggle--row ${on ? 'is-on' : ''}" title="Aplicar a todos los productos activos">
      <input type="checkbox" class="sale-toggle-input" ${on ? 'checked' : ''} ${disabled}
        onchange="changeCategorySale(${cid}, this, true)" aria-label="Rebaja para toda la categoría" />
      <span class="sale-toggle-track" aria-hidden="true"><span class="sale-toggle-thumb"></span></span>
    </label>
  </div>`;
}

async function changeCategorySale(categoryId, input, isToggle) {
  if (!canWriteMasters()) { notifyErr('No tienes permiso para cambiar rebajas.'); return; }
  const wrap = input.closest('.sale-toggle-wrap');
  const checkbox = wrap?.querySelector('.sale-toggle-input');
  const numberInput = wrap?.querySelector('.sale-percent-input');
  let percent = Math.max(1, Math.min(90, Math.round(Number(numberInput?.value) || 25)));
  if (numberInput) numberInput.value = percent;
  const enabled = !!checkbox?.checked;
  try {
    const r = await fetch(`${API}/shop/categories/${categoryId}/sale`, {
      method: 'PATCH', credentials: 'same-origin', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ enabled, percent }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.message || 'No se pudo actualizar la categoría.');
    const row = datosState.rows.find(x => Number(x.category_id) === Number(categoryId));
    if (row) { row.sale_enabled = !!data.sale_enabled; row.sale_percent = Number(data.sale_percent); }
    checkbox.checked = !!data.sale_enabled;
    checkbox.closest('.sale-toggle')?.classList.toggle('is-on', !!data.sale_enabled);
    if (numberInput) numberInput.value = data.sale_percent;
    notifyOk(data.message);
    if (window.tiendaState) { window.tiendaState.loaded = false; }
  } catch (e) {
    if (isToggle && checkbox) checkbox.checked = !enabled;
    notifyErr(e.message || 'No se pudo actualizar la rebaja.');
  }
}

window.changeCategorySale = changeCategorySale;

async function patchProductSale(productId, payload) {
  const r = await fetch(`${API}/shop/products/${productId}/sale`, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.message || 'Error al actualizar rebaja');
  return data;
}

async function toggleProductSale(productId, input) {
  if (!canWriteMasters()) {
    notifyErr('No tienes permiso para cambiar rebajas.');
    input.checked = !input.checked;
    return;
  }
  const enabled = input.checked;
  const wrap = input.closest('.sale-toggle-wrap');
  const label = input.closest('.sale-toggle');
  const pctEl = wrap?.querySelector('.sale-percent-input');
  const percent = Number(pctEl?.value) || 25;
  if (label) label.classList.toggle('is-on', enabled);
  try {
    const data = await patchProductSale(productId, { enabled, percent });
    const row = datosState.rows.find(x => Number(x.product_id) === Number(productId));
    if (row) {
      row.sale_enabled = !!data.sale_enabled;
      row.sale_percent = Number(data.sale_percent) || percent;
    }
    if (label) label.classList.toggle('is-on', !!data.sale_enabled);
    input.checked = !!data.sale_enabled;
    if (pctEl && data.sale_percent != null) pctEl.value = data.sale_percent;
    notifyOk(data.message || 'Rebaja actualizada.');
    refreshTiendaAfterSaleChange(productId, data);
  } catch (e) {
    input.checked = !enabled;
    if (label) label.classList.toggle('is-on', !enabled);
    notifyErr(e.message || 'No se pudo cambiar la rebaja.');
  }
}

async function changeProductSalePercent(productId, input) {
  if (!canWriteMasters()) {
    notifyErr('No tienes permiso para cambiar rebajas.');
    return;
  }
  let percent = Number(input.value);
  if (!Number.isFinite(percent)) percent = 25;
  percent = Math.max(1, Math.min(90, Math.round(percent)));
  input.value = percent;
  const wrap = input.closest('.sale-toggle-wrap');
  const enabled = !!wrap?.querySelector('.sale-toggle-input')?.checked;
  try {
    const data = await patchProductSale(productId, { enabled, percent });
    const row = datosState.rows.find(x => Number(x.product_id) === Number(productId));
    if (row) {
      row.sale_enabled = !!data.sale_enabled;
      row.sale_percent = Number(data.sale_percent) || percent;
    }
    if (data.sale_percent != null) input.value = data.sale_percent;
    notifyOk(enabled ? `Rebaja del ${data.sale_percent}% actualizada.` : `Porcentaje guardado (${data.sale_percent}%). Activa el interruptor para aplicarlo.`);
    refreshTiendaAfterSaleChange(productId, data);
  } catch (e) {
    notifyErr(e.message || 'No se pudo guardar el porcentaje.');
  }
}

window.toggleProductSale = toggleProductSale;
window.changeProductSalePercent = changeProductSalePercent;

function refreshTiendaAfterSaleChange(productId, data) {
  const pid = Number(productId);
  const price = Number(data?.price);
  const compare = Number(data?.compare_at_price || 0);
  if (window.tiendaState?.products?.length) {
    const prod = window.tiendaState.products.find(p => Number(p.product_id) === pid);
    if (prod) {
      prod.variant = prod.variant || {};
      if (Number.isFinite(price)) prod.variant.price = price;
      prod.variant.compare_at_price = compare > 0 ? compare : 0;
    }
    if (typeof filterShopProducts === 'function') filterShopProducts();
  }
  if (typeof invalidatePageCache === 'function') invalidatePageCache('tienda');
  if (typeof loadTiendaProducts === 'function') loadTiendaProducts();
}

function onGestionSearchInput() {
  clearTimeout(gestionSearchTimer);
  gestionSearchTimer = setTimeout(() => {
    datosState.search = (document.getElementById('gestion-search')?.value || '').trim();
    datosState.offset = 0;
    loadMasterRows();
  }, 320);
}

function onGestionStatusChange(value) {
  datosState.activeFilter = value === 'true' || value === 'false' ? value : '';
  datosState.offset = 0;
  loadMasterRows();
}

function onGestionProductFilterChange() {
  datosState.categoryId = (document.getElementById('gestion-category')?.value || '').trim();
  datosState.vendorId = (document.getElementById('gestion-vendor')?.value || '').trim();
  datosState.offset = 0;
  loadMasterRows();
}

function renderGestionProductFilterOptions(options) {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const category = document.getElementById('gestion-category');
  const vendor = document.getElementById('gestion-vendor');
  if (category) {
    category.innerHTML = '<option value="">Todas</option>' + (options?.categories || [])
      .map(row => `<option value="${Number(row.category_id)}">${escape(row.name || `Categoría ${row.category_id}`)}</option>`).join('');
    category.value = datosState.categoryId;
  }
  if (vendor) {
    vendor.innerHTML = '<option value="">Todos</option>' + (options?.vendors || [])
      .map(row => `<option value="${Number(row.vendor_id)}" data-filter-region="${escape(row.region_name || 'Sin región')}" data-filter-country="${escape(row.country || 'Sin país')}">${escape(row.name || `Proveedor ${row.vendor_id}`)}</option>`).join('');
    vendor.value = datosState.vendorId;
  }
}

/** @deprecated usar showGestion / loadGestionPage */
async function loadDatosPage() {
  if (!datosState.table) datosState.table = 'dim_producto';
  await loadGestionPage(true);
}

async function loadMasterTablesList() {
  await loadGestionTablesCache();
}

async function onDatosTableChange() {
  await loadGestionPage(true);
}

function datosCurrentPage() {
  return Math.floor(datosState.offset / datosState.limit);
}

function datosTotalPages() {
  return Math.max(1, Math.ceil((datosState.total || 0) / datosState.limit));
}

function datosGoPage(page) {
  const pages = datosTotalPages();
  const next = Math.max(0, Math.min(page, pages - 1));
  datosState.offset = next * datosState.limit;
  loadMasterRows();
}

function datosSetPageSize(size) {
  const n = Math.max(10, Math.min(200, parseInt(size, 10) || 50));
  datosState.limit = n;
  datosState.offset = 0;
  loadMasterRows();
}

function renderDatosPager() {
  const pager = document.getElementById('datos-pager');
  if (!pager) return;
  const total = datosState.total || 0;
  const limit = datosState.limit;
  const offset = datosState.offset;
  const pages = datosTotalPages();
  const page = datosCurrentPage();
  if (!datosState.table || total <= limit) {
    pager.hidden = true;
    pager.innerHTML = '';
    return;
  }
  const prevDisabled = page <= 0 ? 'disabled' : '';
  const nextDisabled = offset + limit >= total ? 'disabled' : '';
  pager.hidden = false;
  pager.innerHTML = `
    <div class="table-pager-group">
      <label class="table-pager-size" for="datos-page-size">Por página</label>
      <select id="datos-page-size" class="table-pager-select" onchange="datosSetPageSize(this.value)">
        ${[25, 50, 100, 200].map(n => `<option value="${n}" ${n === limit ? 'selected' : ''}>${n}</option>`).join('')}
      </select>
    </div>
    <button type="button" class="btn btn-ghost btn-sm" ${prevDisabled} onclick="datosGoPage(${page - 1})">← Anterior</button>
    <span class="table-pager-info">Página ${page + 1} de ${pages}</span>
    <button type="button" class="btn btn-ghost btn-sm" ${nextDisabled} onclick="datosGoPage(${page + 1})">Siguiente →</button>`;
}

async function loadMasterRows() {
  const table = datosState.table;
  const body = document.getElementById('datos-rows-body');
  const meta = document.getElementById('datos-rows-meta');
  if (!table || !body) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  const q = new URLSearchParams({ limit: datosState.limit, offset: datosState.offset });
  if (datosState.search) q.set('search', datosState.search);
  if (datosState.activeFilter) q.set('active', datosState.activeFilter);
  if (table === 'dim_producto' && datosState.categoryId) q.set('category_id', datosState.categoryId);
  if (table === 'dim_producto' && datosState.vendorId) q.set('vendor_id', datosState.vendorId);
  const r = await fetch(API + '/master/' + encodeURIComponent(table) + '?' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="8">${data.message || 'Error al procesar'}</td></tr>`;
    notifyErr(data.message || 'Error al cargar registros.');
    return;
  }
  datosState.rows = data.rows || [];
  datosState.total = data.total || 0;
  datosState.editable = data.editable === true;
  datosState.fieldLabels = data.field_labels || {};
  datosState.columns = data.columns || (datosState.rows[0] ? Object.keys(datosState.rows[0]) : []);
  if (table === 'dim_producto') renderGestionProductFilterOptions(data.filter_options || {});
  if (table === 'dim_producto') datosState.filterOptions = data.filter_options || {};
  const pages = datosTotalPages();
  if (datosState.total && datosCurrentPage() >= pages) {
    datosState.offset = Math.max(pages - 1, 0) * datosState.limit;
    if (datosState.offset !== (data.offset || 0)) {
      await loadMasterRows();
      return;
    }
  }
  const from = datosState.total ? datosState.offset + 1 : 0;
  const to = Math.min(datosState.offset + datosState.rows.length, datosState.total);
  if (meta) {
    meta.textContent = datosState.total
      ? `Mostrando ${from}–${to} de ${datosState.total} · ${data.label}${!datosState.editable ? ' (solo lectura)' : ''}`
      : `0 registros · ${data.label}${!datosState.editable ? ' (solo lectura)' : ''}`;
  }
  if (!datosState.rows.length) {
    renderDatosPager();
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
  const isProducts = datosState.table === 'dim_producto';
  const isCategories = datosState.table === 'dim_categoria';
  let keys = datosState.columns.length
    ? datosState.columns.filter(k => datosState.rows.length ? k in datosState.rows[0] : true)
    : Object.keys(datosState.rows[0]);
  if (isProducts) keys = keys.filter(k => k !== 'sale_enabled' && k !== 'sale_percent');
  if (isCategories) keys = keys.filter(k => k !== 'sale_enabled' && k !== 'sale_percent');
  const saleHeader = isProducts || isCategories ? '<th class="sale-toggle-col">Rebaja %</th>' : '';
  document.getElementById('datos-rows-head').innerHTML =
    keys.map(k => `<th>${labelForField(k)}</th>`).join('') + '<th>Acciones</th>' + saleHeader;
  body.innerHTML = datosState.rows.map(row => {
    const pk = masterPk(row) ?? row[keys[0]];
    const img = row.image_url || row.src
      ? `<br><img class="master-thumb" src="${row.image_url || row.src}" alt="" />`
      : '';
    const isActive = row.active !== false;
    const actions = canWriteMasters()
      ? `<div class="master-actions table-actions">
          <button type="button" class="btn btn-ghost btn-sm" onclick="openMasterEdit('${pk}')">Editar</button>
          <button type="button" class="btn btn-ghost btn-sm ${isActive ? 'master-disable-btn' : 'master-enable-btn'}"
            onclick="toggleMasterActive('${pk}', ${isActive ? 'false' : 'true'})">${isActive ? 'Inhabilitar' : 'Habilitar'}</button>
        </div>`
      : '<span class="master-note">Sin permiso de escritura</span>';
    const saleCell = isProducts
      ? `<td class="sale-toggle-cell">${renderProductSaleToggle(row)}</td>`
      : isCategories ? `<td class="sale-toggle-cell">${renderCategorySaleToggle(row)}</td>` : '';
    return `<tr>${keys.map(k => `<td>${formatCell(row[k])}${k === 'name' || k === 'title' ? img : ''}</td>`).join('')}
      <td>${actions}</td>${saleCell}</tr>`;
  }).join('');
  renderDatosPager();
}

function formatCell(v) {
  if (v == null) return '—';
  if (typeof v === 'boolean') {
    return v
      ? '<span class="badge badge--ok master-status-badge">Activo</span>'
      : '<span class="badge badge--muted master-status-badge">Inactivo</span>';
  }
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
  if (!canWriteMasters()) { notifyErr('No tienes permiso para editar registros de gestión.'); return; }
  if (!datosState.table) {
    notifyWarn('Elige primero una entidad en el menú Gestión.');
    return;
  }
  if (datosState.editable === false) {
    notifyWarn('Esta tabla no admite edición manual desde aquí.');
    return;
  }
  const meta = gestionTablesCache.find(t => t.name === datosState.table);
  if (meta?.creatable === false) {
    notifyWarn('Este catálogo es fijo. Puedes editar o inhabilitar sus registros, pero no agregar nuevos.');
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
    dim_producto: ['name', 'category_id', 'unit_price', 'unit_cost'],
    dim_canal: ['name', 'description'],
    dim_prioridad: ['code', 'name', 'sla_days', 'description'],
    dim_cliente: ['name', 'country_id', 'channel_id', 'email', 'phone'],
  };
  const fields = samples[datosState.table] || ['name'];
  const intFields = new Set(['region_id', 'country_id', 'category_id', 'channel_id', 'sla_days', 'product_id']);
  const moneyFields = new Set(['unit_price', 'unit_cost']);
  return fields.map(f => {
    if (datosState.table === 'dim_producto' && f === 'category_id') {
      const options = (datosState.filterOptions?.categories || []).map(cat => {
        const selected = Number(row.category_id) === Number(cat.category_id) ? ' selected' : '';
        return `<option value="${Number(cat.category_id)}"${selected}>${String(cat.name || '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}</option>`;
      }).join('');
      return `<div class="fg"><label for="mf-${f}">${labelForField(f)}</label><select id="mf-${f}" required><option value="">— Selecciona una categoría —</option>${options}</select></div>`;
    }
    const inputType = intFields.has(f) || moneyFields.has(f) ? 'number' : 'text';
    const minAttr = intFields.has(f) ? ' min="1" step="1"' : (moneyFields.has(f) ? ' min="0.01" step="0.01"' : '');
    return `
    <div class="fg"><label for="mf-${f}">${labelForField(f)}</label>
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
    dim_producto: ['name', 'category_id', 'unit_price', 'unit_cost'],
    dim_canal: ['name', 'description'],
    dim_prioridad: ['code', 'name', 'sla_days', 'description'],
    dim_cliente: ['name', 'country_id', 'channel_id', 'email', 'phone'],
  };
  const intPositive = new Set(['region_id', 'country_id', 'category_id', 'channel_id', 'sla_days', 'product_id']);
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
  if (!r.ok) { notifyErr(data.message || 'Error al procesar'); return; }
  if (table === 'dim_producto') {
    const file = document.getElementById('master-image-file');
    const prodId = pk || data.row?.product_id;
    if (file && file.files[0] && prodId) await uploadProductImage(prodId, file.files[0]);
  }
  closeMasterForm();
  window.dispatchEvent(new CustomEvent('masterdata:changed', { detail: { table } }));
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

async function toggleMasterActive(pk, active) {
  if (!canWriteMasters()) {
    notifyErr('No tienes permiso para cambiar el estado de registros maestros.');
    return;
  }
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: active ? 'Habilitar registro' : 'Inhabilitar registro',
    message: active
      ? 'El registro volverá a estar disponible para operaciones nuevas.'
      : 'El registro dejará de estar disponible para operaciones nuevas, pero conservará todo su historial.',
    confirmLabel: active ? 'Habilitar' : 'Inhabilitar',
    danger: !active,
  });
  if (!ok) return;
  const r = await fetch(`${API}/master/${datosState.table}/${pk}/status`, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: !!active }),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error al procesar'); return; }
  notifyOk(data.message || (active ? 'Registro habilitado.' : 'Registro inhabilitado.'));
  window.dispatchEvent(new CustomEvent('masterdata:changed', { detail: { table: datosState.table } }));
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
    st.textContent = '✗ ' + (data.message || 'Error al procesar');
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
    const topo = d.topology || meta.topology || {};
    const c = d.counts || {};
    const ready = d.strategic_ready ?? meta.strategic_ready;
    const lagging = d.strategic_lagging ?? meta.strategic_lagging;
    const msg = d.strategic_message || meta.message || '';
    const factN = (c.fact_ventas ?? meta.fact_ventas_count ?? 0).toLocaleString('es');
    const landingN = (c.sales_records ?? meta.sales_records_count ?? 0).toLocaleString('es');
    const statusCls = ready ? (lagging ? 'elt-status-banner--warn' : 'elt-status-banner--ok') : 'elt-status-banner--empty';
    const statusTitle = ready
      ? (lagging ? 'Capa estratégica activa (con retraso de sync)' : 'Capa estratégica lista')
      : 'Capa estratégica vacía';
    const mongoLine = topo.split_enabled
      ? `<p><strong>Bases Mongo:</strong> operativa <code>${topo.ops_database || '—'}</code> · almacén <code>${topo.dw_database || '—'}</code></p>`
      : `<p><strong>Base de datos:</strong> ${d.mongo_db || topo.dw_database || '—'}</p>`;
    el.innerHTML = `
      <div class="elt-status-banner ${statusCls}">
        <strong>${statusTitle}</strong>
        <p>${msg || (ready ? 'Tablero e Informes compuestos (RC) pueden consultar fact_ventas.' : 'Ejecuta la carga ELT o el DAG Airflow para poblar fact_ventas.')}</p>
        ${ready ? '<button type="button" class="btn btn-primary btn-sm" onclick="showPage(\'reportes-compuestos\')">Ver informes compuestos</button>' : ''}
        ${!ready ? '<button type="button" class="btn btn-ghost btn-sm" data-require-perm="elt.run" onclick="goConstruirModelo()">Ir a Construir modelo</button>' : ''}
      </div>
      ${mongoLine}
      <p><strong>CSV:</strong> ${d.csv_exists ? '✓' : '✗'} ${d.csv_source || ''}</p>
      <p><strong>Parquet:</strong> ${d.parquet_exists ? '✓' : '✗'}</p>
      <p style="font-family:var(--mono);font-size:11px;margin-top:8px">
        sales_records: ${landingN} · fact_ventas: ${factN} ·
        dim_producto: ${(c.dim_producto ?? '—').toLocaleString?.('es') ?? c.dim_producto} · solicitudes: ${(c.purchase_requests ?? '—').toLocaleString?.('es') ?? c.purchase_requests}
      </p>
      ${d.last_build || meta.last_build ? `<p style="font-size:12px"><strong>Último build ELT:</strong> ${d.last_build || meta.last_build}</p>` : ''}
      <p style="margin-top:8px;font-size:12px">
        Orquestación: DAG Airflow <code>globtrade_strategic_etl</code>
        (<a href="http://localhost:8080" target="_blank" rel="noopener">localhost:8080</a>) —
        rebuild truncate+reload para Tablero e Informes RC.
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
let auditState = { page: 0, role: '', module: '', action: '', email: '', dateFrom: '', dateTo: '', rows: [] };

function auditGoPage(page) {
  auditState.page = Math.max(0, page);
  loadAuditPage();
}

function auditFormatAt(value) {
  const raw = String(value || '').trim();
  if (!raw) return '—';
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return new Intl.DateTimeFormat('es-EC', {
    timeZone: window.ALTAVIA_TIMEZONE || 'America/Guayaquil',
    year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false,
  }).format(date);
}

function auditActionBadge(action) {
  const a = String(action || '').toLowerCase();
  let cls = 'badge badge--neutral audit-action';
  if (a.includes('delete') || a.includes('inhabilit') || a.includes('reject')) cls = 'badge badge--danger audit-action';
  else if (a.includes('create') || a.includes('habilit') || a.includes('approve')) cls = 'badge badge--ok audit-action';
  else if (a.includes('update') || a.includes('edit') || a.includes('patch')) cls = 'badge badge--info audit-action';
  return `<span class="${cls}">${action || '—'}</span>`;
}

function auditReadFilters() {
  auditState.role = document.getElementById('audit-role-filter')?.value || '';
  auditState.module = document.getElementById('audit-module-filter')?.value || '';
  auditState.action = document.getElementById('audit-action-filter')?.value || '';
  auditState.email = document.getElementById('audit-user-filter')?.value.trim() || '';
  auditState.dateFrom = document.getElementById('audit-date-from')?.value || '';
  auditState.dateTo = document.getElementById('audit-date-to')?.value || '';
}

function auditParams(includePaging = true) {
  auditReadFilters();
  const params = new URLSearchParams();
  if (includePaging) {
    params.set('limit', String(AUDIT_PAGE_SIZE));
    params.set('offset', String(auditState.page * AUDIT_PAGE_SIZE));
  }
  [['role', auditState.role], ['module', auditState.module], ['action', auditState.action],
    ['email', auditState.email], ['date_from', auditState.dateFrom], ['date_to', auditState.dateTo]]
    .forEach(([key, value]) => { if (value) params.set(key, value); });
  return params;
}

async function showAuditDetail(index) {
  const row = auditState.rows[index] || {};
  const changes = row.changes || {};
  const labels = {
    export: 'Exportación de informe', update_profile: 'Actualización del perfil', shop_sync: 'Sincronización de la tienda',
    product_sale_toggle: 'Cambio de descuento del producto', category_sale_toggle: 'Cambio de descuento de la categoría',
    create_request: 'Creación de solicitud', issue_invoice: 'Emisión de factura', enable: 'Habilitación', disable: 'Inhabilitación',
    rows: 'Registros incluidos', format: 'Formato', filters: 'Filtros aplicados', email_changed: 'Correo modificado',
    password_changed: 'Contraseña modificada', role: 'Rol', action: 'Acción', module: 'Módulo', entity: 'Entidad',
    date_from: 'Fecha desde', date_to: 'Fecha hasta', before: 'Antes', after: 'Después'
  };
  const friendly = value => {
    if (value === null || value === undefined || value === '') return 'Sin dato';
    if (typeof value === 'boolean') return value ? 'Sí' : 'No';
    if (Array.isArray(value)) return value.length ? value.map(friendly).join(', ') : 'Ninguno';
    if (typeof value === 'object') {
      const entries = Object.entries(value).filter(([, val]) => val !== null && val !== '' && val !== undefined);
      return entries.length ? entries.map(([key, val]) => `${labels[key] || key}: ${friendly(val)}`).join('; ') : 'Ninguno';
    }
    return String(value);
  };
  const lines = Object.entries(changes).map(([field, values]) => {
    const name = labels[field] || field.replaceAll('_', ' ');
    if (values && typeof values === 'object' && ('before' in values || 'after' in values)) {
      return `${name}: ${friendly(values.before)} → ${friendly(values.after)}`;
    }
    return `${name}: ${friendly(values)}`;
  });
  const details = row.details || {};
  const fallbackLines = Object.entries(details).map(([field, value]) => `${labels[field] || field.replaceAll('_', ' ')}: ${friendly(value)}`);
  const fallback = fallbackLines.length ? fallbackLines.join('\n') : 'Sin información adicional.';
  const message = lines.length ? lines.join('\n') : fallback;
  if (typeof opsConfirm === 'function') {
    await opsConfirm({ title: labels[row.action] || row.action || 'Detalle de la acción', message, confirmLabel: 'Cerrar' });
  } else window.alert(message);
}

function exportAuditLog() {
  const api = window.API || (window.location.origin + '/api');
  window.location.assign(`${api}/audit_log/export?${auditParams(false)}`);
}

async function loadAuditPage() {
  const body = document.getElementById('audit-body');
  const meta = document.getElementById('audit-meta');
  const pager = document.getElementById('audit-pager');
  const roleSel = document.getElementById('audit-role-filter');
  if (!body) return;
  const api = window.API || (window.location.origin + '/api');
  const cols = 8;
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
  auditReadFilters();
  body.innerHTML = `<tr><td colspan="${cols}">Cargando auditoría…</td></tr>`;
  if (meta) meta.textContent = 'Cargando…';
  if (pager) pager.innerHTML = '';
  const params = auditParams(true);
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
    const fillAuditSelect = (id, values, current, emptyLabel) => {
      const select = document.getElementById(id);
      if (!select || !Array.isArray(values)) return;
      select.innerHTML = `<option value="">${emptyLabel}</option>${values.map(value =>
        `<option value="${value}" ${value === current ? 'selected' : ''}>${value}</option>`).join('')}`;
    };
    fillAuditSelect('audit-module-filter', data.modules, auditState.module, 'Todos');
    fillAuditSelect('audit-action-filter', data.actions, auditState.action, 'Todas');
    const rows = data.entries || [];
    auditState.rows = rows;
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
      <td>${e.module || 'gestión'}</td>
      <td>${auditActionBadge(e.action)}</td>
      <td>${e.entity || '—'}</td>
      <td class="audit-cell-user">${e.email || '—'}</td>
      <td><code>${e.role || '—'}</code></td>
      <td class="audit-cell-id">${e.entity_id ?? '—'}</td>
      <td><button type="button" class="btn btn-ghost btn-sm" onclick="showAuditDetail(${auditState.rows.indexOf(e)})">Ver cambios</button></td>
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

window.showGestion = showGestion;
window.loadGestionPage = loadGestionPage;
window.onGestionSearchInput = onGestionSearchInput;
window.showAuditDetail = showAuditDetail;
window.exportAuditLog = exportAuditLog;
window.auditGoPage = auditGoPage;
window.loadAuditPage = loadAuditPage;
window.datosGoPage = datosGoPage;
window.datosSetPageSize = datosSetPageSize;
