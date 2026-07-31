/* Utilidades UI operativa: toast + empty states */
(function () {
  function ensureToastHost() {
    let host = document.getElementById('ops-toast-host');
    if (host) return host;
    host = document.createElement('div');
    host.id = 'ops-toast-host';
    host.className = 'ops-toast-host';
    host.setAttribute('aria-live', 'polite');
    document.body.appendChild(host);
    return host;
  }

  window.opsToast = function opsToast(message, type, opts) {
    const o = opts || {};
    const host = ensureToastHost();
    const el = document.createElement('div');
    el.className = 'ops-toast ops-toast--' + (type || 'info');
    const hasAction = o.actionLabel && typeof o.action === 'function';
    if (hasAction) {
      el.classList.add('ops-toast--action');
      const text = document.createElement('span');
      text.className = 'ops-toast-msg';
      text.textContent = String(message || '');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-primary btn-ops ops-toast-btn';
      btn.textContent = o.actionLabel;
      btn.addEventListener('click', () => {
        el.classList.remove('ops-toast--show');
        setTimeout(() => el.remove(), 220);
        o.action();
      });
      el.appendChild(text);
      el.appendChild(btn);
    } else {
      el.textContent = String(message || '');
    }
    host.appendChild(el);
    requestAnimationFrame(() => el.classList.add('ops-toast--show'));
    const ttl = hasAction ? 8000 : 2800;
    setTimeout(() => {
      el.classList.remove('ops-toast--show');
      setTimeout(() => el.remove(), 220);
    }, ttl);
  };

  window.goConstruirModelo = function goConstruirModelo() {
    const nav = document.querySelector('.nav-item[data-page="datos"]');
    if (typeof showPage === 'function') showPage('datos', nav || undefined);
    setTimeout(() => {
      const btn = document.querySelector('#page-datos button[onclick="runBuildModel()"]');
      if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
  };

  window.syncStaleAnalytics = async function syncStaleAnalytics() {
    const API = (window.location.origin || 'http://127.0.0.1:5001') + '/api';
    try {
      const r = await fetch(API + '/analytics/sync-stale', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 50 }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        opsToast(data.message || 'No se pudo sincronizar (¿permiso ELT?)', 'danger');
        return;
      }
      const n = (data.orders_synced || []).length;
      opsToast(
        n
          ? `Sincronizados ${n} pedido(s) → fact_ventas (${data.facts_inserted || 0} hechos).`
          : (data.message || 'Nada pendiente de sync.'),
        data.strategic_lagging ? 'warn' : 'ok'
      );
      if (typeof loadDashboard === 'function') loadDashboard();
    } catch (e) {
      opsToast(e.message || 'Error de sync', 'danger');
    }
  };

  window.opsEmpty = function opsEmpty(opts) {
    const o = opts || {};
    const title = o.title || 'Sin datos';
    const hint = o.hint || '';
    const cta = o.ctaLabel
      ? `<button type="button" class="btn btn-primary btn-ops" onclick="${o.ctaOnclick || ''}">${o.ctaLabel}</button>`
      : '';
    return `<div class="ops-empty">
      <strong class="ops-empty-title">${title}</strong>
      ${hint ? `<p class="ops-empty-hint">${hint}</p>` : ''}
      ${cta ? `<div class="ops-empty-actions">${cta}</div>` : ''}
    </div>`;
  };

  window.opsEmptyRow = function opsEmptyRow(colspan, opts) {
    return `<tr><td colspan="${colspan || 6}">${opsEmpty(opts)}</td></tr>`;
  };

  window.opsConfirm = function opsConfirm(message) {
    return window.confirm(message);
  };
})();
