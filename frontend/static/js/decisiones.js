/* Panel Decisiones — margen, stock, embudo */
let decisionesActiveView = 'portfolio';

const DECISION_VIEWS = [
  { id: 'portfolio', label: 'Portafolio', hint: 'Comprar, impulsar o liquidar' },
  { id: 'forecast', label: 'Pronóstico', hint: 'Demanda y compra sugerida' },
  { id: 'profit', label: 'Rentabilidad', hint: 'Pedidos y utilidad real' },
  { id: 'suppliers', label: 'Proveedores', hint: 'Ganancia y dependencia' },
  { id: 'signals', label: 'Señales', hint: 'Embudo, stock y canales' },
];

function setDecisionesView(view) {
  decisionesActiveView = DECISION_VIEWS.some(v => v.id === view) ? view : 'portfolio';
  document.querySelectorAll('[data-dec-view]').forEach(el => {
    el.hidden = el.dataset.decView !== decisionesActiveView;
  });
  document.querySelectorAll('.dec-view-tab').forEach(btn => {
    const active = btn.dataset.view === decisionesActiveView;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function installDecisionesViews(root) {
  if (!root) return;
  const nav = document.createElement('div');
  nav.className = 'dec-view-tabs';
  nav.setAttribute('role', 'group');
  nav.setAttribute('aria-label', 'Vistas del centro de decisiones');
  nav.innerHTML = DECISION_VIEWS.map(v => `
    <button type="button" class="dec-view-tab" data-view="${v.id}" onclick="setDecisionesView('${v.id}')">
      <strong>${v.label}</strong><span>${v.hint}</span>
    </button>`).join('');
  root.prepend(nav);

  const children = [...root.children].filter(el => !el.classList.contains('dec-view-tabs'));
  const views = [
    'portfolio', 'portfolio', 'portfolio', 'portfolio',
    'forecast', 'forecast', 'forecast',
    'profit', 'profit', 'profit',
    'suppliers', 'suppliers', 'suppliers',
    'signals', 'signals', 'signals', 'signals',
  ];
  children.forEach((el, index) => {
    el.dataset.decView = views[index] || 'signals';
  });
  setDecisionesView(decisionesActiveView);
}

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

function decEsc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function decPortfolioMatrix(items) {
  const rows = (items || []).filter(r => Number(r.revenue) >= 0 && Number.isFinite(Number(r.margin_pct)));
  if (!rows.length) return '<div class="rc-chart-empty">La matriz aparecerá después de publicar ventas por producto en ClickHouse.</div>';
  const width = 920, height = 330, left = 70, right = 24, top = 34, bottom = 58;
  const plotW = width - left - right, plotH = height - top - bottom;
  const maxRevenue = Math.max(1, ...rows.map(r => Number(r.revenue) || 0));
  const x = value => left + Math.log1p(Math.max(0,Number(value)||0)) / Math.log1p(maxRevenue) * plotW;
  const margins=rows.map(r=>Number(r.margin_pct)||0),minMargin=Math.min(-10,...margins),maxMargin=Math.max(50,...margins);
  const y = value => top + (maxMargin-Math.max(minMargin,Math.min(maxMargin,Number(value)||0))) / (maxMargin-minMargin) * plotH;
  const medianRevenue = [...rows].map(r => Number(r.revenue) || 0).sort((a,b) => a-b)[Math.floor(rows.length / 2)] || 0;
  const dividerX = x(medianRevenue), dividerY = y(20);
  const colors = { 'Estrella': '#16a34a', 'Oportunidad': '#0284c7', 'Volumen con margen débil': '#d97706', 'Revisar portafolio': '#dc2626' };
  const dots = rows.slice(0, 35).map(r => `<g><circle cx="${x(r.revenue)}" cy="${y(r.margin_pct)}" r="7" fill="${colors[r.quadrant] || '#64748b'}" opacity=".86"><title>${decEsc(r.product)} · ${fmtPct(r.margin_pct)} · ${decMoney(r.revenue)}</title></circle></g>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Matriz de ventas y margen por producto">
    <rect x="${left}" y="${top}" width="${dividerX-left}" height="${dividerY-top}" fill="#e0f2fe" opacity=".65"/>
    <rect x="${dividerX}" y="${top}" width="${width-right-dividerX}" height="${dividerY-top}" fill="#dcfce7" opacity=".65"/>
    <rect x="${left}" y="${dividerY}" width="${dividerX-left}" height="${top+plotH-dividerY}" fill="#fee2e2" opacity=".65"/>
    <rect x="${dividerX}" y="${dividerY}" width="${width-right-dividerX}" height="${top+plotH-dividerY}" fill="#fef3c7" opacity=".65"/>
    <line x1="${dividerX}" y1="${top}" x2="${dividerX}" y2="${top+plotH}" stroke="#94a3b8" stroke-dasharray="5 5"/>
    <line x1="${left}" y1="${dividerY}" x2="${width-right}" y2="${dividerY}" stroke="#94a3b8" stroke-dasharray="5 5"/>
    <text x="${(left+dividerX)/2}" y="${top+18}" text-anchor="middle" font-size="11" font-weight="700" fill="#0369a1">OPORTUNIDAD</text>
    <text x="${(dividerX+width-right)/2}" y="${top+18}" text-anchor="middle" font-size="11" font-weight="700" fill="#15803d">ESTRELLA</text>
    <text x="${(left+dividerX)/2}" y="${top+plotH-10}" text-anchor="middle" font-size="11" font-weight="700" fill="#b91c1c">REVISAR</text>
    <text x="${(dividerX+width-right)/2}" y="${top+plotH-10}" text-anchor="middle" font-size="11" font-weight="700" fill="#b45309">MARGEN DÉBIL</text>
    ${dots}
    <text x="${left+plotW/2}" y="${height-10}" text-anchor="middle" font-size="12" fill="#64748b">Ingresos →</text>
    <text x="18" y="${top+plotH/2}" text-anchor="middle" transform="rotate(-90 18 ${top+plotH/2})" font-size="12" fill="#64748b">Margen % →</text>
  </svg>`;
}

function renderDecisionesPanel(data) {
  const root = document.getElementById('decisiones-root');
  if (!root) return;
  const margin = data.margin || {};
  const stock = data.stock || {};
  const funnel = data.funnel || {};
  const channels = data.channels || [];
  const alerts = data.alerts || [];
  const portfolio = data.portfolio || {};
  const portfolioSummary = portfolio.summary || {};
  const forecast = data.forecast || {};
  const forecastSummary = forecast.summary || {};
  const profitability = data.profitability || {};
  const profitSummary = profitability.summary || {};
  const suppliers = data.suppliers || {};
  const supplierSummary = suppliers.summary || {};

  const forecastRows = (forecast.items || []).map(r => `
    <tr>
      <td><strong>${r.product || '—'}</strong><br><span class="catalog-meta">${r.category || '—'}</span></td>
      <td>${fmtNum(r.forecast_total)} uds<br><span class="catalog-meta">${(r.forecast || []).map(v => fmtNum(v)).join(' · ')}</span></td>
      <td>${fmtNum(r.stock)}</td>
      <td><strong>${fmtNum(r.recommended_purchase)}</strong></td>
      <td>${r.trend_pct > 0 ? '+' : ''}${fmtPct(r.trend_pct)}</td>
      <td><span class="dec-quadrant">${r.confidence || '—'} · ${r.confidence_pct || 0}%</span></td>
      <td class="dec-decision-cell">${r.decision || '—'}</td>
    </tr>`).join('') || `<tr><td colspan="7">${forecast.message || 'Se necesitan al menos tres meses de ventas por producto.'}</td></tr>`;

  const trueProfitRows = (profitability.products || []).map(r => `
    <tr>
      <td><strong>${r.product || '—'}</strong>${r.estimated ? '<br><span class="catalog-meta">Costo incompleto: resultado estimado</span>' : ''}</td>
      <td>${decMoney(r.revenue)}</td><td>${decMoney(r.cost)}</td><td>${decMoney(r.expenses)}</td>
      <td class="${Number(r.profit) < 0 ? 'text-danger' : ''}"><strong>${decMoney(r.profit)}</strong></td>
      <td>${fmtPct(r.margin_pct)}</td><td>${fmtNum(r.orders)}</td>
    </tr>`).join('') || '<tr><td colspan="7">Todavía no hay pedidos convertidos con líneas de costo.</td></tr>';

  const lossOrderRows = (profitability.orders || []).slice(0, 10).map(r => `
    <tr><td><strong>${r.order_id || ('Solicitud #' + r.request_id)}</strong><br><span class="catalog-meta">${r.client || 'Sin cliente'}</span></td>
      <td>${decMoney(r.net_revenue)}</td><td>${decMoney(r.discount)}</td><td>${decMoney(r.refund)}</td>
      <td>${decMoney(r.product_cost + r.shipping_cost + r.tax)}</td><td><strong>${decMoney(r.net_profit)}</strong></td><td>${fmtPct(r.margin_pct)}</td></tr>`).join('') || '<tr><td colspan="7">Sin pedidos para analizar.</td></tr>';

  const portfolioRows = (portfolio.items || []).map(r => `
    <tr>
      <td><strong>${r.product || '—'}</strong><br><span class="catalog-meta">${r.category || '—'}</span></td>
      <td><span class="dec-quadrant dec-quadrant--${String(r.quadrant || '').toLowerCase().replace(/[^a-z]+/g, '-')}">${r.quadrant || '—'}</span></td>
      <td>${decMoney(r.revenue)}<br><span class="catalog-meta">${fmtPct(r.margin_pct)} margen</span></td>
      <td>${fmtNum(r.stock)}${r.stock_estimated?'*':''}<br><span class="catalog-meta">${r.stock_estimated?'Estimación temporal':(r.coverage_days == null ? 'Sin velocidad' : r.coverage_days + ' días')}</span></td>
      <td>${r.days_without_sale == null ? 'Sin ventas registradas' : r.days_without_sale + ' días'}</td>
      <td><strong>${r.reorder_qty > 0 ? fmtNum(r.reorder_qty) + ' uds' : '—'}</strong></td>
      <td class="dec-decision-cell">${r.decision || '—'}</td>
    </tr>`).join('') || `<tr><td colspan="7">${portfolio.message || 'Sin datos de producto publicados en ClickHouse.'}</td></tr>`;

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
    <div class="dec-section-head">
      <div><span class="page-badge">Portafolio estratégico · ${portfolio.lookback_days || 90} días</span><h2>Qué comprar, impulsar o liquidar</h2></div>
      <span class="rc-source-badge">${portfolio.source || 'ClickHouse'}</span>
    </div>
    <div class="dec-kpis dec-kpis--portfolio">
      <div class="stat-card"><div class="stat-value">${portfolioSummary.stars ?? 0}</div><div class="stat-label">Productos estrella</div></div>
      <div class="stat-card"><div class="stat-value">${portfolioSummary.reorder_products ?? 0}</div><div class="stat-label">Requieren reposición</div></div>
      <div class="stat-card"><div class="stat-value">${portfolioSummary.stagnant_products ?? 0}</div><div class="stat-label">Productos sin rotación</div></div>
      <div class="stat-card"><div class="stat-value">${decMoney(portfolioSummary.capital_at_risk)}</div><div class="stat-label">Capital en riesgo</div></div>
    </div>

    <section class="table-box dec-portfolio-matrix">
      <div class="table-header"><div class="table-title">Matriz de portafolio</div><span class="dash-records-meta">Ingresos frente a margen</span></div>
      <div class="dec-matrix-wrap">${decPortfolioMatrix(portfolio.items)}</div>
    </section>

    <section class="table-box dec-portfolio-table">
      <div class="table-header">
        <div class="table-title">Rentabilidad y decisión por producto</div>
        <span class="dash-records-meta">${portfolioSummary.products || 0} productos${portfolioSummary.estimated_stock_products?` · ${portfolioSummary.estimated_stock_products} existencias estimadas`:''}</span>
      </div>
      <div class="table-scroll"><table>
        <thead><tr><th>Producto</th><th>Clasificación</th><th>Rentabilidad</th><th>Stock / cobertura</th><th>Sin vender</th><th>Reponer</th><th>Decisión recomendada</th></tr></thead>
        <tbody>${portfolioRows}</tbody>
      </table></div>
    </section>

    <div class="dec-section-head dec-section-head--signals">
      <div><span class="page-badge">Pronóstico de demanda</span><h2>Qué se venderá y cuánto comprar</h2></div>
      <span class="rc-source-badge">${forecast.source || 'ClickHouse'}</span>
    </div>
    <div class="dec-kpis">
      <div class="stat-card"><div class="stat-value">${fmtNum(forecastSummary.forecast_units || 0)}</div><div class="stat-label">Unidades previstas (${forecast.horizon || 3} meses)</div></div>
      <div class="stat-card"><div class="stat-value">${fmtNum(forecastSummary.purchase_units || 0)}</div><div class="stat-label">Compra sugerida</div></div>
      <div class="stat-card"><div class="stat-value">${forecastSummary.products || 0}</div><div class="stat-label">Productos modelados</div></div>
      <div class="stat-card"><div class="stat-value">${forecastSummary.low_confidence || 0}</div><div class="stat-label">Pronósticos de baja confianza</div></div>
    </div>
    <section class="table-box">
      <div class="table-header"><div class="table-title">Demanda prevista por producto</div><span class="dash-records-meta">${forecast.method || ''}</span></div>
      <div class="table-scroll"><table><thead><tr><th>Producto</th><th>Pronóstico</th><th>Stock</th><th>Comprar</th><th>Tendencia</th><th>Confianza</th><th>Decisión</th></tr></thead><tbody>${forecastRows}</tbody></table></div>
    </section>

    <div class="dec-section-head dec-section-head--signals">
      <div><span class="page-badge">Rentabilidad real</span><h2>Qué pedidos y productos dejan dinero</h2></div>
      <span class="rc-source-badge">Contabilidad operativa</span>
    </div>
    <div class="dec-kpis">
      <div class="stat-card"><div class="stat-value">${decMoney(profitSummary.net_revenue)}</div><div class="stat-label">Ingreso después de devoluciones</div></div>
      <div class="stat-card"><div class="stat-value">${decMoney(profitSummary.net_profit)}</div><div class="stat-label">Utilidad neta calculada</div></div>
      <div class="stat-card"><div class="stat-value">${fmtPct(profitSummary.net_margin_pct)}</div><div class="stat-label">Margen neto</div></div>
      <div class="stat-card"><div class="stat-value">${profitSummary.loss_orders || 0}</div><div class="stat-label">Pedidos con pérdida</div></div>
    </div>
    <div class="dec-grid">
      <section class="table-box">
        <div class="table-header"><div class="table-title">Productos menos rentables primero</div><span class="dash-records-meta">${profitability.method || ''}</span></div>
        <div class="table-scroll"><table><thead><tr><th>Producto</th><th>Ingreso</th><th>Costo</th><th>Otros gastos</th><th>Utilidad</th><th>Margen</th><th>Pedidos</th></tr></thead><tbody>${trueProfitRows}</tbody></table></div>
      </section>
      <section class="table-box">
        <div class="table-header"><div class="table-title">Pedidos que requieren revisión</div><span class="dash-records-meta">Descuentos, devoluciones, costo, envío e impuesto</span></div>
        <div class="table-scroll"><table><thead><tr><th>Pedido</th><th>Ingreso neto</th><th>Descuento</th><th>Devolución</th><th>Costos</th><th>Utilidad</th><th>Margen</th></tr></thead><tbody>${lossOrderRows}</tbody></table></div>
      </section>
    </div>

    <div class="dec-section-head dec-section-head--signals">
      <div><span class="page-badge">Proveedores estratégicos</span><h2>A quién comprarle más y a quién renegociar</h2></div>
      <span class="rc-source-badge">${suppliers.source || 'ClickHouse'}</span>
    </div>
    <div class="dec-kpis">
      <div class="stat-card"><div class="stat-value">${supplierSummary.providers || 0}</div><div class="stat-label">Proveedores analizados</div></div>
      <div class="stat-card"><div class="stat-value">${decMoney(supplierSummary.profit)}</div><div class="stat-label">Utilidad asociada</div></div>
      <div class="stat-card"><div class="stat-value">${fmtPct(supplierSummary.return_pct)}</div><div class="stat-label">Retorno sobre compras</div></div>
      <div class="stat-card"><div class="stat-value">${supplierSummary.providers_to_review || 0}</div><div class="stat-label">Proveedores por revisar</div></div>
    </div>
    <section class="table-box">
      <div class="table-header">
        <div class="table-title">Rentabilidad por proveedor</div>
        <span class="dash-records-meta">Mejor proveedor: ${decEsc(supplierSummary.best_provider || '—')}</span>
      </div>
      <p class="dec-insight">${suppliers.method || suppliers.message || ''}</p>
      <div class="table-scroll"><table>
        <thead><tr><th>Proveedor</th><th>Pedidos</th><th>Compras</th><th>Ingresos</th><th>Utilidad</th><th>Margen</th><th>Retorno</th><th>Decisión</th></tr></thead>
        <tbody>${(suppliers.items || []).map(r => `
          <tr>
            <td><strong>${decEsc(r.proveedor || '—')}</strong><br><span class="catalog-meta">${fmtNum(r.unidades)} uds · ${fmtNum(r.ordenes_compra)} OC</span></td>
            <td>${fmtNum(r.pedidos)}</td>
            <td>${decMoney(r.compras)}</td>
            <td>${decMoney(r.ingresos)}</td>
            <td class="${Number(r.utilidad) < 0 ? 'text-danger' : ''}"><strong>${decMoney(r.utilidad)}</strong></td>
            <td>${fmtPct(r.margen_pct)}</td>
            <td>${fmtPct(r.retorno_pct)}</td>
            <td class="dec-decision-cell">${decEsc(r.decision || '—')}</td>
          </tr>`).join('') || '<tr><td colspan="8">Ejecuta la sincronización con ClickHouse para ver proveedores estratégicos.</td></tr>'}</tbody>
      </table></div>
    </section>

    <div class="dec-section-head dec-section-head--signals"><h2>Señales operativas y comerciales</h2></div>
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
  installDecisionesViews(root);
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
window.setDecisionesView = setDecisionesView;
window.decGo = decGo;
window.decGoLowStock = decGoLowStock;
window.decRestockPO = decRestockPO;
