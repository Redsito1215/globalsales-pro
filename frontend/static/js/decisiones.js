/* Panel Decisiones — margen, stock, embudo */
async function loadDecisionesPage() {
  const root = document.getElementById('decisiones-root');
  if (!root) return;
  if (!window._authUser) {
    root.innerHTML = '<p class="catalog-empty">Inicia sesión para ver el panel de decisiones.</p>';
    return;
  }
  if (!hasPermission('decisiones.view')) {
    root.innerHTML = '<p class="catalog-empty">Tu rol no tiene acceso a Decisiones.</p>';
    return;
  }
  root.innerHTML = '<p class="catalog-empty">Calculando señales de negocio…</p>';
  const days = document.getElementById('dec-days')?.value || '7';
  const thr = document.getElementById('dec-stock-thr')?.value || '20';
  const q = new URLSearchParams({ days, stock_threshold: thr, limit: 8 });
  try {
    const r = await fetch(API + '/decisiones/panel?' + q, { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) {
      root.innerHTML = `<p class="catalog-empty">${data.message || 'Error al cargar decisiones'}</p>`;
      return;
    }
    renderDecisionesPanel(data);
  } catch (e) {
    root.innerHTML = `<p class="catalog-empty">Error de red: ${e.message}</p>`;
  }
}

function decMoney(n) {
  return '$' + Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function decAlertClass(level) {
  if (level === 'danger') return 'dec-alert dec-alert--danger';
  if (level === 'warn') return 'dec-alert dec-alert--warn';
  if (level === 'ok') return 'dec-alert dec-alert--ok';
  if (level === 'info') return 'dec-alert dec-alert--info';
  return 'dec-alert';
}

function renderDecisionesPanel(data) {
  const root = document.getElementById('decisiones-root');
  if (!root) return;
  const margin = data.margin || {};
  const stock = data.stock || {};
  const funnel = data.funnel || {};
  const channels = data.channels || [];
  const alerts = data.alerts || [];

  const topRows = (margin.top || []).map(r => `
    <tr>
      <td>${r.item_type}</td>
      <td>${fmtPct(r.margin_pct)}</td>
      <td>${decMoney(r.profit)}</td>
      <td>${decMoney(r.revenue)}</td>
      <td>${fmtNum(r.orders)}</td>
    </tr>`).join('') || '<tr><td colspan="5">Sin datos de margen. Carga el dataset histórico.</td></tr>';

  const bottomRows = (margin.bottom || []).map(r => `
    <tr>
      <td>${r.item_type}</td>
      <td>${fmtPct(r.margin_pct)}</td>
      <td>${decMoney(r.profit)}</td>
      <td>${decMoney(r.revenue)}</td>
      <td>${fmtNum(r.orders)}</td>
    </tr>`).join('') || '<tr><td colspan="5">Sin datos.</td></tr>';

  const stockRows = (stock.items || []).map(r => {
    const sug = Math.max(20 - Number(r.inventory_quantity || 0), 10);
    const vid = Number(r.variant_id || 0);
    const vendorId = Number(r.vendor_id || 0);
    const cost = Number(r.cost || 0);
    const canPo = typeof hasPermission === 'function' && hasPermission('compras.manage') && vid > 0;
    return `<tr>
      <td>${r.title}<br><span style="font-size:10px;color:var(--muted)">${r.sku || ''} · ${r.vendor}</span></td>
      <td><strong>${r.inventory_quantity}</strong></td>
      <td>${decMoney(r.price)}</td>
      <td>${decMoney(r.cost)}</td>
      <td>${canPo
        ? `<button type="button" class="btn btn-primary btn-ops" onclick="decRestockPO(${vid},${vendorId},${cost},${sug})">Crear OC</button>`
        : '—'}</td>
    </tr>`;
  }).join('') || `<tr><td colspan="5">${stock.insight || 'Sin referencias con existencias bajas'}</td></tr>`;

  const funnelMax = Math.max(1, ...(funnel.stages || []).map(s => s.count || 0));
  const funnelBars = (funnel.stages || []).map(s => {
    const pct = Math.round(((s.count || 0) / funnelMax) * 100);
    return `<div class="dec-funnel-row">
      <span class="dec-funnel-label">${s.label}</span>
      <div class="dec-funnel-track"><div class="dec-funnel-fill" style="width:${pct}%"></div></div>
      <span class="dec-funnel-n">${s.count || 0}</span>
    </div>`;
  }).join('');

  const channelRows = channels.map(c => `
    <tr>
      <td>${c.channel}</td>
      <td>${fmtPct(c.margin_pct)}</td>
      <td>${decMoney(c.profit)}</td>
      <td>${decMoney(c.revenue)}</td>
    </tr>`).join('') || '<tr><td colspan="4">Sin canales</td></tr>';

  const alertsHtml = alerts.map(a => `
    <button type="button" class="${decAlertClass(a.level)}" onclick="decGo('${a.action || 'dashboard'}')">
      <strong>${a.title}</strong>
      <span>${a.detail || ''}</span>
    </button>`).join('');

  root.innerHTML = `
    <div class="dec-kpis">
      <div class="stat-card"><div class="stat-value">${funnel.total_created ?? 0}</div><div class="stat-label">Solicitudes (${funnel.days || 7}d)</div></div>
      <div class="stat-card"><div class="stat-value">${funnel.conversion_rate != null ? funnel.conversion_rate + '%' : '—'}</div><div class="stat-label">Tasa conversión</div></div>
      <div class="stat-card"><div class="stat-value">${funnel.awaiting_action ?? 0}</div><div class="stat-label">Por gestionar</div></div>
      <div class="stat-card"><div class="stat-value">${stock.low_count ?? 0}</div><div class="stat-label">Referencias con existencias bajas</div></div>
    </div>

    <div class="dec-alerts">${alertsHtml}</div>

    <div class="dec-grid">
      <section class="table-box">
        <div class="table-header">
          <div class="table-title">Mejor margen (priorizar)</div>
          <span class="dash-records-meta">${margin.total_categories || 0} categorías</span>
        </div>
        <p class="dec-insight">${margin.insight || ''}</p>
        <div class="table-scroll"><table>
          <thead><tr><th>Producto</th><th>Margen</th><th>Utilidad</th><th>Ingreso</th><th>Pedidos</th></tr></thead>
          <tbody>${topRows}</tbody>
        </table></div>
      </section>

      <section class="table-box">
        <div class="table-header">
          <div class="table-title">Peor margen (revisar / salir)</div>
        </div>
        <div class="table-scroll"><table>
          <thead><tr><th>Producto</th><th>Margen</th><th>Utilidad</th><th>Ingreso</th><th>Pedidos</th></tr></thead>
          <tbody>${bottomRows}</tbody>
        </table></div>
      </section>

      <section class="table-box">
        <div class="table-header">
          <div class="table-title">Embudo comercial</div>
          <span class="dash-records-meta">desde ${funnel.since || '—'}</span>
        </div>
        <p class="dec-insight">${funnel.insight || ''}</p>
        <div class="dec-funnel">${funnelBars}</div>
        <div style="margin-top:12px">
          <button type="button" class="btn btn-ghost" onclick="decGo('ventas')">Ir a bandeja comercial</button>
        </div>
      </section>

      <section class="table-box">
        <div class="table-header">
          <div class="table-title">Existencias bajas (≤ ${stock.threshold ?? 20})</div>
          <span class="dash-records-meta">${stock.low_count || 0} / ${stock.total_skus || 0} referencias</span>
        </div>
        <p class="dec-insight">${stock.insight || ''}</p>
        <div class="table-scroll"><table>
          <thead><tr><th>Producto</th><th>Existencias</th><th>Precio</th><th>Costo</th><th></th></tr></thead>
          <tbody>${stockRows}</tbody>
        </table></div>
        <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn btn-primary btn-ops" onclick="decGo('compras')">Ir a Compras / Existencias</button>
          <button type="button" class="btn btn-ghost btn-ops" onclick="decGoLowStock()">Ver inventario bajo</button>
        </div>
      </section>

      <section class="table-box dec-span-2">
        <div class="table-header"><div class="table-title">Canales por margen</div></div>
        <div class="table-scroll"><table>
          <thead><tr><th>Canal</th><th>Margen</th><th>Utilidad</th><th>Ingreso</th></tr></thead>
          <tbody>${channelRows}</tbody>
        </table></div>
      </section>
    </div>
  `;
}

function decGo(page) {
  const btn = document.querySelector('.nav-item[data-page="' + page + '"]');
  if (typeof showPage === 'function') showPage(page, btn || null);
}

function decGoLowStock() {
  window._comprasPrefill = { lowOnly: true };
  decGo('compras');
}

function decRestockPO(variantId, vendorId, unitCost, qty) {
  window._comprasPrefill = {
    tab: 'ocs',
    variant_id: variantId,
    vendor_id: vendorId || null,
    unit_cost: unitCost || 0,
    quantity: qty || 10,
  };
  decGo('compras');
}

window.loadDecisionesPage = loadDecisionesPage;
window.decGo = decGo;
window.decGoLowStock = decGoLowStock;
window.decRestockPO = decRestockPO;
