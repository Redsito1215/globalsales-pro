/* Panel administrativo de políticas y condiciones comerciales. */
const commercialState = { discounts: [], customers: [], products: [], activeTab: 'policies' };

function commercialEsc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function commercialMoney(value) {
  return '$' + Number(value || 0).toLocaleString('es-EC', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
async function commercialFetch(url, options = {}) {
  const response = await fetch(url, {headers: {'Content-Type':'application/json', ...(options.headers || {})}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || data.code || 'No se pudo completar la operación.');
  return data;
}

function showCommercialTab(tab, button) {
  commercialState.activeTab = tab;
  document.querySelectorAll('.commercial-panel').forEach(el => { el.hidden = el.id !== `commercial-panel-${tab}`; });
  document.querySelectorAll('[data-commercial-tab]').forEach(el => el.classList.toggle('is-active', el === button || el.dataset.commercialTab === tab));
  if (tab === 'discounts') loadCommercialDiscounts();
  if (tab === 'exceptions') loadCommercialExceptions();
  if (tab === 'customers') loadCommercialCustomers();
  if (tab === 'products') loadCommercialProducts();
}

async function loadCommercialAdminPage() {
  if (!window._authUser || !hasPermission('users.manage')) return;
  try {
    const data = await commercialFetch('/api/shop/commercial/settings');
    const s = data.settings || {};
    document.getElementById('commercial-min-order').value = s.minimum_order_amount || 0;
    document.getElementById('commercial-max-order').value = s.maximum_order_amount || 0;
    document.getElementById('commercial-min-margin').value = s.minimum_margin_pct || 0;
    document.getElementById('commercial-default-limit').value = s.default_customer_limit || 0;
    showCommercialTab(commercialState.activeTab);
  } catch (error) { notifyErr(error.message); }
}

async function saveCommercialSettings(event) {
  event.preventDefault();
  const body = {
    minimum_order_amount: Number(document.getElementById('commercial-min-order').value || 0),
    maximum_order_amount: Number(document.getElementById('commercial-max-order').value || 0),
    minimum_margin_pct: Number(document.getElementById('commercial-min-margin').value || 0),
    default_customer_limit: Number(document.getElementById('commercial-default-limit').value || 0),
  };
  try {
    const data = await commercialFetch('/api/shop/commercial/settings', {method:'PATCH', body:JSON.stringify(body)});
    notifyOk(data.message || 'Políticas comerciales guardadas.');
  } catch (error) { notifyErr(error.message); }
}

async function loadCommercialDiscounts() {
  const body = document.getElementById('commercial-discounts-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="8">Cargando…</td></tr>';
  try {
    const data = await commercialFetch('/api/shop/commercial/discounts');
    commercialState.discounts = data.discounts || [];
    body.innerHTML = commercialState.discounts.length ? commercialState.discounts.map((d, index) => `<tr>
      <td><strong>${commercialEsc(d.code)}</strong></td><td>${d.value_type === 'fixed' ? 'Valor fijo' : 'Porcentaje'}</td>
      <td>${d.value_type === 'fixed' ? commercialMoney(d.value) : `${Number(d.value)}%`}</td>
      <td>${commercialEsc(d.valid_from || 'Sin inicio')} → ${commercialEsc(d.valid_to || 'Sin vencimiento')}</td>
      <td>${Number(d.usage_count || 0)} / ${Number(d.usage_limit || 0) || '∞'}</td><td>${commercialEsc((d.allowed_segments || []).join(', ') || 'Todos')}</td>
      <td><span class="commercial-status ${d.currently_valid ? 'is-ok' : 'is-muted'}">${d.currently_valid ? 'Vigente' : (d.active ? 'Fuera de vigencia' : 'Inactivo')}</span></td>
      <td><button class="btn btn-ghost btn-sm" onclick="editCommercialDiscount(${index})">Editar</button></td></tr>`).join('') : '<tr><td colspan="8">No hay descuentos registrados.</td></tr>';
  } catch (error) { body.innerHTML = `<tr><td colspan="8">${commercialEsc(error.message)}</td></tr>`; }
}

function editCommercialDiscount(index) {
  const d = commercialState.discounts[index]; if (!d) return;
  document.getElementById('discount-code').value = d.code || '';
  document.getElementById('discount-type').value = d.value_type || 'percentage';
  document.getElementById('discount-value').value = d.value || '';
  document.getElementById('discount-minimum').value = d.minimum_order_amount || 0;
  document.getElementById('discount-from').value = d.valid_from || '';
  document.getElementById('discount-to').value = d.valid_to || '';
  document.getElementById('discount-usage-limit').value = d.usage_limit || 0;
  document.getElementById('discount-segments').value = (d.allowed_segments || []).join(', ');
  document.getElementById('discount-active').checked = d.active !== false;
  document.getElementById('discount-code').focus();
}

async function saveCommercialDiscount(event) {
  event.preventDefault();
  const body = {
    code: document.getElementById('discount-code').value,
    value_type: document.getElementById('discount-type').value,
    value: Number(document.getElementById('discount-value').value),
    minimum_order_amount: Number(document.getElementById('discount-minimum').value || 0),
    valid_from: document.getElementById('discount-from').value || null,
    valid_to: document.getElementById('discount-to').value || null,
    usage_limit: Number(document.getElementById('discount-usage-limit').value || 0),
    allowed_segments: document.getElementById('discount-segments').value.split(',').map(x => x.trim()).filter(Boolean),
    active: document.getElementById('discount-active').checked,
  };
  try {
    const data = await commercialFetch('/api/shop/commercial/discounts', {method:'POST', body:JSON.stringify(body)});
    notifyOk(data.message || 'Descuento guardado.'); await loadCommercialDiscounts();
  } catch (error) { notifyErr(error.message); }
}

async function loadCommercialExceptions() {
  const body = document.getElementById('commercial-exceptions-body'); if (!body) return;
  const status = document.getElementById('commercial-exception-status')?.value || '';
  try {
    const data = await commercialFetch('/api/shop/commercial/exceptions' + (status ? `?status=${encodeURIComponent(status)}` : ''));
    const rows = data.exceptions || [];
    body.innerHTML = rows.length ? rows.map(row => `<tr><td>${row.exception_id}</td><td>${commercialEsc(row.customer_email)}</td><td>${commercialMoney(row.amount)}</td><td>${commercialEsc((row.violations || []).join(', '))}</td><td>${commercialEsc(row.reason)}</td><td><span class="commercial-status status-${commercialEsc(row.status)}">${commercialEsc(row.status)}</span></td><td>${row.status === 'pending' ? `<button class="btn btn-primary btn-sm" onclick="decideCommercialException(${row.exception_id},true)">Aprobar</button> <button class="btn btn-ghost btn-sm" onclick="decideCommercialException(${row.exception_id},false)">Rechazar</button>` : '—'}</td></tr>`).join('') : '<tr><td colspan="7">No hay excepciones con este estado.</td></tr>';
  } catch (error) { body.innerHTML = `<tr><td colspan="7">${commercialEsc(error.message)}</td></tr>`; }
}

async function decideCommercialException(id, approved) {
  const reason = prompt(approved ? 'Motivo de aprobación (mínimo 8 caracteres):' : 'Motivo de rechazo (mínimo 8 caracteres):');
  if (!reason) return;
  try {
    const data = await commercialFetch(`/api/shop/commercial/exceptions/${id}/decision`, {method:'POST', body:JSON.stringify({approved, reason})});
    notifyOk(data.message || 'Excepción resuelta.'); await loadCommercialExceptions();
  } catch (error) { notifyErr(error.message); }
}

async function loadCommercialCustomers() {
  const body = document.getElementById('commercial-customers-body'); if (!body) return;
  const q = document.getElementById('commercial-customer-search')?.value || '';
  try {
    const data = await commercialFetch(`/api/master/dim_cliente?limit=100&search=${encodeURIComponent(q)}`);
    commercialState.customers = data.rows || [];
    body.innerHTML = commercialState.customers.length ? commercialState.customers.map((c, index) => `<tr><td><strong>${commercialEsc(c.name || 'Cliente')}</strong><br><small>${commercialEsc(c.email)}</small></td><td><select id="cust-segment-${c.client_id}">${['nuevo','ocasional','frecuente','vip','riesgo'].map(x => `<option value="${x}" ${c.segment===x?'selected':''}>${x}</option>`).join('')}</select></td><td><input class="commercial-table-input" id="cust-purchase-${c.client_id}" type="number" min="0" step="0.01" value="${Number(c.purchase_limit || 0)}"></td><td><input id="cust-credit-${c.client_id}" type="checkbox" ${c.credit_enabled?'checked':''}></td><td><input class="commercial-table-input" id="cust-limit-${c.client_id}" type="number" min="0" step="0.01" value="${Number(c.credit_limit || 0)}"></td><td><input class="commercial-table-input" id="cust-days-${c.client_id}" type="number" min="1" max="365" value="${Number(c.credit_days || 30)}"></td><td><button class="btn btn-primary btn-sm" onclick="saveCommercialCustomer(${c.client_id},${index})">Guardar</button></td></tr>`).join('') : '<tr><td colspan="7">No se encontraron clientes.</td></tr>';
  } catch (error) { body.innerHTML = `<tr><td colspan="6">${commercialEsc(error.message)}</td></tr>`; }
}

async function saveCommercialCustomer(id, index) {
  const email = commercialState.customers[index]?.email || '';
  const payload = {segment:document.getElementById(`cust-segment-${id}`).value, purchase_limit:Number(document.getElementById(`cust-purchase-${id}`).value || 0), credit_enabled:document.getElementById(`cust-credit-${id}`).checked, credit_limit:Number(document.getElementById(`cust-limit-${id}`).value || 0), credit_days:Number(document.getElementById(`cust-days-${id}`).value || 30)};
  try { const data = await commercialFetch(`/api/shop/commercial/customers/${encodeURIComponent(email)}`, {method:'PATCH', body:JSON.stringify(payload)}); notifyOk(data.message || 'Cliente actualizado.'); }
  catch (error) { notifyErr(error.message); }
}
async function refreshCommercialSegments() {
  try { const data = await commercialFetch('/api/shop/commercial/segments/refresh', {method:'POST', body:JSON.stringify({limit:5000})}); notifyOk(`${data.count || 0} segmentos actualizados.`); await loadCommercialCustomers(); }
  catch (error) { notifyErr(error.message); }
}

async function loadCommercialProducts() {
  const body = document.getElementById('commercial-products-body'); if (!body) return;
  const q = (document.getElementById('commercial-product-search')?.value || '').toLowerCase();
  try {
    const data = await commercialFetch('/api/shop/products?limit=100');
    commercialState.products = (data.products || []).filter(p => !q || String(p.product_id).includes(q) || String(p.title || '').toLowerCase().includes(q));
    body.innerHTML = commercialState.products.length ? commercialState.products.map(p => `<tr><td>${p.product_id}</td><td><strong>${commercialEsc(p.title)}</strong><br><small>${commercialEsc(p.variant?.sku || '')}</small></td><td>${commercialMoney(p.variant?.price)}</td><td>${commercialMoney(p.variant?.cost)}</td><td><input type="checkbox" ${p.featured?'checked':''} onchange="setCommercialFeatured(${p.product_id},this.checked)"></td><td><button class="btn btn-ghost btn-sm" onclick="loadCommercialHistory(${p.product_id},decodeURIComponent('${encodeURIComponent(p.title || '')}'))">Ver historial</button></td></tr>`).join('') : '<tr><td colspan="6">No se encontraron productos.</td></tr>';
  } catch (error) { body.innerHTML = `<tr><td colspan="6">${commercialEsc(error.message)}</td></tr>`; }
}
async function setCommercialFeatured(id, featured) {
  try { const data = await commercialFetch(`/api/shop/products/${id}/featured`, {method:'PATCH', body:JSON.stringify({featured})}); notifyOk(data.message || 'Producto actualizado.'); }
  catch (error) { notifyErr(error.message); await loadCommercialProducts(); }
}
async function loadCommercialHistory(id, title) {
  const box = document.getElementById('commercial-history-box'), body = document.getElementById('commercial-history-body');
  try {
    const data = await commercialFetch(`/api/shop/products/${id}/price-history`); const rows = data.history || [];
    document.getElementById('commercial-history-title').textContent = `Historial · ${title}`; box.hidden = false;
    body.innerHTML = rows.length ? rows.map(r => `<tr><td>${commercialEsc((r.effective_from || '').slice(0,19))}</td><td>${commercialEsc((r.effective_to || 'Actual').slice(0,19))}</td><td>${commercialMoney(r.unit_price)}</td><td>${commercialMoney(r.unit_cost)}</td><td>${r.sale_enabled ? `${r.sale_percent || 0}%` : 'No'}</td><td>${Number(r.margin_pct || 0).toFixed(2)}%</td></tr>`).join('') : '<tr><td colspan="6">Aún no hay cambios registrados.</td></tr>';
    box.scrollIntoView({behavior:'smooth', block:'nearest'});
  } catch (error) { notifyErr(error.message); }
}
