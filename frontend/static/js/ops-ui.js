/* Utilidades UI operativa: toast + empty states (sin alert nativo) */
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

  /**
   * Feedback flotante (desaparece solo; sin botón Aceptar del navegador).
   * type: ok | warn | danger | info
   */
  window.opsToast = function opsToast(message, type, opts) {
    const o = opts || {};
    const host = ensureToastHost();
    const el = document.createElement('div');
    const kind = type || 'info';
    el.className = 'ops-toast ops-toast--' + kind;
    el.setAttribute('role', kind === 'danger' || kind === 'warn' ? 'alert' : 'status');
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
    const ttl = o.ttl || (hasAction ? 8000 : kind === 'danger' ? 4500 : 3200);
    setTimeout(() => {
      el.classList.remove('ops-toast--show');
      setTimeout(() => el.remove(), 220);
    }, ttl);
  };

  /** Alias corto usado en toda la SPA */
  window.notify = function notify(message, type, opts) {
    if (typeof window.opsToast === 'function') {
      window.opsToast(message, type || 'info', opts);
      return;
    }
    console.log('[notify]', type || 'info', message);
  };
  window.notifyOk = function (msg, opts) { window.notify(msg, 'ok', opts); };
  window.notifyErr = function (msg, opts) { window.notify(msg, 'danger', opts); };
  window.notifyWarn = function (msg, opts) { window.notify(msg, 'warn', opts); };

  window.goConstruirModelo = function goConstruirModelo() {
    const nav = document.querySelector('.nav-item[data-page="datos"]');
    if (typeof showPage === 'function') showPage('datos', nav || undefined);
    setTimeout(() => {
      const btn = document.querySelector('#page-datos button[onclick="runBuildModel()"]');
      if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
  };

  window.syncStaleAnalytics = async function syncStaleAnalytics(opts) {
    const silent = !!(opts && opts.silent);
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
        if (!silent) notifyErr(data.message || 'No se pudo sincronizar (¿permiso ELT?)');
        return data;
      }
      const n = (data.orders_synced || []).length;
      if (!silent) {
        notify(
          n
            ? `Sincronizados ${n} pedido(s) → fact_ventas (${data.facts_inserted || 0} hechos).`
            : (data.message || 'Nada pendiente de sync.'),
          data.strategic_lagging ? 'warn' : 'ok'
        );
      }
      if (!silent && typeof loadDashboard === 'function') loadDashboard();
      return data;
    } catch (e) {
      if (!silent) notifyErr(e.message || 'Error de sync');
      return null;
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

  window.PAYMENT_METHOD_OPTIONS = {
    offline: [
      { value: 'tarjeta', label: 'Tarjeta' },
      { value: 'efectivo_tarjeta', label: 'Efectivo y tarjeta bancaria' },
    ],
    online: [
      { value: 'tarjeta', label: 'Tarjeta' },
      { value: 'credito', label: 'Crédito' },
      { value: 'cuenta_bancaria', label: 'Cuenta bancaria' },
    ],
  };

  window.fillPaymentMethodSelect = function fillPaymentMethodSelect(selectEl, offline) {
    if (!selectEl) return;
    const opts = offline ? PAYMENT_METHOD_OPTIONS.offline : PAYMENT_METHOD_OPTIONS.online;
    selectEl.innerHTML = opts.map(o => `<option value="${o.value}">${o.label}</option>`).join('');
  };

  function ensureConfirmModal() {
    let modal = document.getElementById('ops-confirm-modal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'ops-confirm-modal';
    modal.className = 'modal';
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    modal.innerHTML = `
      <div class="modal-backdrop" data-ops-confirm-cancel></div>
      <div class="modal-card" role="dialog" aria-labelledby="ops-confirm-title">
        <h2 id="ops-confirm-title">Confirmar</h2>
        <p id="ops-confirm-message" class="modal-sub"></p>
        <div class="ops-confirm-actions">
          <button type="button" class="btn btn-primary" id="ops-confirm-ok">Confirmar</button>
          <button type="button" class="btn btn-ghost" id="ops-confirm-cancel">Cancelar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    return modal;
  }

  /**
   * Confirmación en modal propio (sin alert/confirm del navegador).
   * Acepta string o { title, message, confirmLabel, cancelLabel, danger }.
   * Devuelve Promise<boolean>.
   */
  window.opsConfirm = function opsConfirm(messageOrOpts) {
    const opts = typeof messageOrOpts === 'string'
      ? { message: messageOrOpts }
      : (messageOrOpts || {});
    return new Promise((resolve) => {
      const modal = ensureConfirmModal();
      const titleEl = document.getElementById('ops-confirm-title');
      const msgEl = document.getElementById('ops-confirm-message');
      const okBtn = document.getElementById('ops-confirm-ok');
      const cancelBtn = document.getElementById('ops-confirm-cancel');
      const backdrop = modal.querySelector('[data-ops-confirm-cancel]');
      let settled = false;

      titleEl.textContent = opts.title || 'Confirmar';
      msgEl.textContent = opts.message || '';
      okBtn.textContent = opts.confirmLabel || 'Confirmar';
      cancelBtn.textContent = opts.cancelLabel || 'Cancelar';
      okBtn.className = 'btn ' + (opts.danger ? 'btn-danger' : 'btn-primary');

      function finish(result) {
        if (settled) return;
        settled = true;
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        backdrop.removeEventListener('click', onCancel);
        document.removeEventListener('keydown', onKey);
        resolve(result);
      }
      function onOk(e) {
        e.preventDefault();
        e.stopPropagation();
        finish(true);
      }
      function onCancel(e) {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        finish(false);
      }
      function onKey(e) {
        if (e.key === 'Escape') onCancel(e);
      }

      okBtn.addEventListener('click', onOk);
      cancelBtn.addEventListener('click', onCancel);
      backdrop.addEventListener('click', onCancel);
      document.addEventListener('keydown', onKey);
      modal.hidden = false;
      modal.setAttribute('aria-hidden', 'false');
      requestAnimationFrame(() => okBtn.focus());
    });
  };

  function ensurePromptModal() {
    let modal = document.getElementById('ops-prompt-modal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'ops-prompt-modal';
    modal.className = 'modal';
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    modal.innerHTML = `
      <div class="modal-backdrop" data-ops-prompt-cancel></div>
      <div class="modal-card" role="dialog" aria-labelledby="ops-prompt-title">
        <h2 id="ops-prompt-title">Ingresar valor</h2>
        <p id="ops-prompt-message" class="modal-sub"></p>
        <div class="fg">
          <label id="ops-prompt-label" for="ops-prompt-input">Valor</label>
          <input type="text" id="ops-prompt-input" autocomplete="off" />
        </div>
        <p id="ops-prompt-error" class="login-error" role="alert" hidden></p>
        <div class="ops-confirm-actions">
          <button type="button" class="btn btn-primary" id="ops-prompt-ok">Aceptar</button>
          <button type="button" class="btn btn-ghost" id="ops-prompt-cancel">Cancelar</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    return modal;
  }

  /**
   * Entrada en modal propio (sin prompt del navegador).
   * Devuelve Promise<string|null> — null si canceló.
   */
  window.opsPrompt = function opsPrompt(opts) {
    const o = opts || {};
    return new Promise((resolve) => {
      const modal = ensurePromptModal();
      const titleEl = document.getElementById('ops-prompt-title');
      const msgEl = document.getElementById('ops-prompt-message');
      const labelEl = document.getElementById('ops-prompt-label');
      const inputEl = document.getElementById('ops-prompt-input');
      const errEl = document.getElementById('ops-prompt-error');
      const okBtn = document.getElementById('ops-prompt-ok');
      const cancelBtn = document.getElementById('ops-prompt-cancel');
      const backdrop = modal.querySelector('[data-ops-prompt-cancel]');
      let settled = false;

      titleEl.textContent = o.title || 'Ingresar valor';
      msgEl.textContent = o.message || '';
      labelEl.textContent = o.label || 'Valor';
      inputEl.type = o.inputType === 'number' ? 'number' : 'text';
      if (o.inputType === 'number') {
        inputEl.min = o.min != null ? String(o.min) : '0';
        inputEl.step = o.step != null ? String(o.step) : '1';
      } else {
        inputEl.removeAttribute('min');
        inputEl.removeAttribute('step');
      }
      inputEl.value = o.defaultValue != null ? String(o.defaultValue) : '';
      errEl.hidden = true;
      errEl.textContent = '';
      okBtn.textContent = o.confirmLabel || 'Aceptar';
      cancelBtn.textContent = o.cancelLabel || 'Cancelar';

      function finish(result) {
        if (settled) return;
        settled = true;
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        backdrop.removeEventListener('click', onCancel);
        inputEl.removeEventListener('keydown', onKey);
        document.removeEventListener('keydown', onDocKey);
        resolve(result);
      }

      function onOk(e) {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        const val = inputEl.value.trim();
        if (typeof o.validate === 'function') {
          const err = o.validate(val);
          if (err) {
            errEl.textContent = err;
            errEl.hidden = false;
            inputEl.focus();
            return;
          }
        }
        finish(val);
      }

      function onCancel(e) {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        finish(null);
      }

      function onKey(e) {
        if (e.key === 'Enter') onOk(e);
      }

      function onDocKey(e) {
        if (e.key === 'Escape') onCancel(e);
      }

      okBtn.addEventListener('click', onOk);
      cancelBtn.addEventListener('click', onCancel);
      backdrop.addEventListener('click', onCancel);
      inputEl.addEventListener('keydown', onKey);
      document.addEventListener('keydown', onDocKey);
      modal.hidden = false;
      modal.setAttribute('aria-hidden', 'false');
      requestAnimationFrame(() => {
        inputEl.focus();
        inputEl.select();
      });
    });
  };
})();
