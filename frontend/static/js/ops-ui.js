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
    const nav = document.querySelector('.nav-item[data-gestion-table="dim_producto"]')
      || document.querySelector('.nav-item[data-page="gestion"]');
    if (typeof showGestion === 'function') showGestion('dim_producto', nav || undefined);
    else if (typeof showPage === 'function') showPage('gestion', nav || undefined);
    setTimeout(() => {
      const btn = document.querySelector('#page-gestion button[onclick="runBuildModel()"]');
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
        signal: AbortSignal.timeout(25000),
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
            : (data.message || 'Nada pendiente de sincronizar.'),
          data.strategic_lagging ? 'warn' : 'ok'
        );
      }
      if (!silent && typeof loadDashboard === 'function') {
        if (typeof clearAnalyticsCache === 'function') clearAnalyticsCache();
        loadDashboard(true);
      }
      if (typeof refreshAnalyticsLagBanners === 'function') refreshAnalyticsLagBanners();
      return data;
    } catch (e) {
      if (!silent) notifyErr(e.message || 'Error al sincronizar');
      return null;
    }
  };

  window.syncOrderAnalytics = async function syncOrderAnalytics(orderId, opts) {
    const silent = !!(opts && opts.silent);
    if (!orderId) return null;
    const API = (window.location.origin || 'http://127.0.0.1:5001') + '/api';
    try {
      const r = await fetch(API + '/analytics/sync-order', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: String(orderId) }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        if (!silent) notifyWarn(data.message || 'No se pudo sincronizar el pedido al tablero.');
        return data;
      }
      if (!silent) {
        const n = data.synced || 0;
        notifyOk(n ? `Pedido ${orderId} sincronizado (${n} hecho(s)).` : `Pedido ${orderId} ya estaba en fact_ventas.`);
      }
      if (typeof refreshAnalyticsLagBanners === 'function') refreshAnalyticsLagBanners();
      if (!silent && typeof loadDashboard === 'function') {
        if (typeof clearAnalyticsCache === 'function') clearAnalyticsCache();
        loadDashboard(true);
      }
      return data;
    } catch (e) {
      if (!silent) notifyErr(e.message || 'Error al sincronizar pedido');
      return null;
    }
  };

  window.refreshAnalyticsLagBanners = async function refreshAnalyticsLagBanners() {
    const API = (window.location.origin || 'http://127.0.0.1:5001') + '/api';
    let lagging = false;
    try {
      const r = await fetch(API + '/meta/data-layers', { credentials: 'same-origin' });
      const data = await r.json().catch(() => ({}));
      lagging = !!(data.strategic_lagging || (data.bridge && data.bridge.strategic_lagging));
    } catch { /* ignore */ }
    const html = lagging
      ? `<p>Hay ventas nuevas pendientes de actualizar en el tablero estratégico.</p>
        <div class="dash-lag-actions">
          <button type="button" class="btn btn-primary btn-sm" data-require-perm="elt.run" onclick="syncStaleAnalytics()">Sincronizar ahora</button>
        </div>`
      : '';
    ['dash-lag-banner', 'ventas-lag-banner'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (lagging) {
        el.hidden = false;
        el.innerHTML = html;
        if (typeof applyPermissionUi === 'function') applyPermissionUi();
      } else {
        el.hidden = true;
        el.innerHTML = '';
      }
    });
    return lagging;
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
    card: [{ value: 'tarjeta', label: 'Tarjeta' }],
  };

  window.resetPagoCardForm = function resetPagoCardForm() {
    ['pago-card-name', 'pago-card-number', 'pago-card-exp', 'pago-card-cvv'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    if (typeof clearPagoFieldErrors === 'function') clearPagoFieldErrors();
    if (typeof updatePagoCardPreview === 'function') updatePagoCardPreview();
    const proc = document.getElementById('pago-processing');
    const actions = document.getElementById('pago-actions');
    const card = document.querySelector('.modal-card--pago');
    if (proc) proc.hidden = true;
    if (actions) actions.hidden = false;
    if (card) card.classList.remove('is-processing');
    const formErr = document.getElementById('pago-form-error');
    if (formErr) {
      formErr.hidden = true;
      formErr.textContent = '';
    }
  };

  window.formatPagoCardNumber = function formatPagoCardNumber(value) {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 16);
    return digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
  };

  window.formatPagoCardExpiry = function formatPagoCardExpiry(value) {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 4);
    if (digits.length <= 2) return digits;
    return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  };

  window.parseCardExpiry = function parseCardExpiry(exp) {
    const trimmed = String(exp || '').trim();
    if (!/^\d{2}\/\d{2}$/.test(trimmed)) {
      return { ok: false, reason: 'format' };
    }
    const mm = parseInt(trimmed.slice(0, 2), 10);
    const yy = parseInt(trimmed.slice(3, 5), 10);
    if (!Number.isFinite(mm) || !Number.isFinite(yy) || mm < 1 || mm > 12) {
      return { ok: false, reason: 'month' };
    }
    const year = 2000 + yy;
    const expiresAt = new Date(year, mm, 0, 23, 59, 59, 999);
    return { ok: true, mm, yy, year, expiresAt };
  };

  window.isCardExpiryPast = function isCardExpiryPast(expiresAt) {
    return expiresAt.getTime() < Date.now();
  };

  window.validatePagoCardExpiryField = function validatePagoCardExpiryField() {
    const exp = (document.getElementById('pago-card-exp')?.value || '').trim();
    if (!exp) {
      setPagoFieldError('exp', '');
      return true;
    }
    const parsed = parseCardExpiry(exp);
    if (!parsed.ok) {
      if (parsed.reason === 'month') {
        setPagoFieldError('exp', 'Mes de vencimiento no válido (MM/AA).');
      } else {
        setPagoFieldError('exp', 'Usa el formato MM/AA.');
      }
      return false;
    }
    if (isCardExpiryPast(parsed.expiresAt)) {
      setPagoFieldError('exp', 'La tarjeta está vencida.');
      return false;
    }
    setPagoFieldError('exp', '');
    return true;
  };

  window.detectPagoCardBrand = function detectPagoCardBrand(number) {
    const digits = String(number || '').replace(/\D/g, '');
    if (/^4/.test(digits)) return 'VISA';
    if (/^(5[1-5]|2[2-7])/.test(digits)) return 'MASTERCARD';
    if (/^3[47]/.test(digits)) return 'AMEX';
    if (/^6/.test(digits)) return 'DISCOVER';
    return 'TARJETA';
  };

  window.maskPagoCardNumber = function maskPagoCardNumber(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return '•••• •••• •••• ••••';
    const padded = (digits + '••••••••••••••••').slice(0, 16);
    return padded.replace(/(.{4})/g, '$1 ').trim();
  };

  window.updatePagoCardPreview = function updatePagoCardPreview() {
    const name = (document.getElementById('pago-card-name')?.value || '').trim();
    const number = document.getElementById('pago-card-number')?.value || '';
    const exp = (document.getElementById('pago-card-exp')?.value || '').trim();
    const brand = document.getElementById('pago-card-brand');
    const numEl = document.getElementById('pago-card-preview-number');
    const nameEl = document.getElementById('pago-card-preview-name');
    const expEl = document.getElementById('pago-card-preview-exp');
    const digits = String(number).replace(/\D/g, '');
    if (brand) brand.textContent = detectPagoCardBrand(digits);
    if (numEl) numEl.textContent = maskPagoCardNumber(number);
    if (nameEl) nameEl.textContent = (name || 'NOMBRE APELLIDO').toUpperCase();
    if (expEl) expEl.textContent = exp || 'MM/AA';
  };

  window.clearPagoFieldErrors = function clearPagoFieldErrors() {
    document.querySelectorAll('.pago-field.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
    document.querySelectorAll('.pago-field-error').forEach((el) => {
      el.hidden = true;
      el.textContent = '';
    });
    const formErr = document.getElementById('pago-form-error');
    if (formErr) {
      formErr.hidden = true;
      formErr.textContent = '';
    }
  };

  window.setPagoFieldError = function setPagoFieldError(field, message) {
    const wrap = document.querySelector(`.pago-field[data-pago-field="${field}"]`);
    const err = document.getElementById(`pago-error-${field}`);
    if (wrap) wrap.classList.toggle('is-invalid', !!message);
    if (err) {
      err.hidden = !message;
      err.textContent = message || '';
    }
  };

  window.luhnCheck = function luhnCheck(number) {
    const digits = String(number || '').replace(/\D/g, '');
    if (digits.length < 13) return false;
    let sum = 0;
    let alt = false;
    for (let i = digits.length - 1; i >= 0; i -= 1) {
      let n = parseInt(digits[i], 10);
      if (alt) {
        n *= 2;
        if (n > 9) n -= 9;
      }
      sum += n;
      alt = !alt;
    }
    return sum % 10 === 0;
  };

  window.isPagoCardNumberFormatValid = function isPagoCardNumberFormatValid(number) {
    const digits = String(number || '').replace(/\D/g, '');
    return digits.length >= 13 && digits.length <= 19;
  };

  window.validatePagoCardForm = function validatePagoCardForm() {
    clearPagoFieldErrors();
    const name = (document.getElementById('pago-card-name')?.value || '').trim();
    const number = String(document.getElementById('pago-card-number')?.value || '').replace(/\D/g, '');
    const exp = (document.getElementById('pago-card-exp')?.value || '').trim();
    const cvv = String(document.getElementById('pago-card-cvv')?.value || '').replace(/\D/g, '');
    let ok = true;
    if (!name || name.length < 3) {
      setPagoFieldError('name', 'Indica el nombre del titular.');
      ok = false;
    }
    if (!isPagoCardNumberFormatValid(number)) {
      setPagoFieldError('number', 'Ingresa un número de tarjeta de 13 a 19 dígitos.');
      ok = false;
    }
    if (!/^\d{2}\/\d{2}$/.test(exp)) {
      setPagoFieldError('exp', 'Usa el formato MM/AA.');
      ok = false;
    } else {
      const parsed = parseCardExpiry(exp);
      if (!parsed.ok) {
        setPagoFieldError(
          'exp',
          parsed.reason === 'month' ? 'Mes de vencimiento no válido (MM/AA).' : 'Usa el formato MM/AA.',
        );
        ok = false;
      } else if (isCardExpiryPast(parsed.expiresAt)) {
        setPagoFieldError('exp', 'La tarjeta está vencida.');
        ok = false;
      }
    }
    if (cvv.length < 3) {
      setPagoFieldError('cvv', 'Ingresa el CVV (3 o 4 dígitos).');
      ok = false;
    }
    if (!ok) {
      const formErr = document.getElementById('pago-form-error');
      if (formErr) {
        formErr.hidden = false;
        formErr.textContent = 'Revisa los datos de la tarjeta antes de continuar.';
      }
      return 'Revisa los datos de la tarjeta.';
    }
    return '';
  };

  window.setPagoProcessing = function setPagoProcessing(active, text) {
    const card = document.querySelector('.modal-card--pago');
    const proc = document.getElementById('pago-processing');
    const actions = document.getElementById('pago-actions');
    const textEl = document.getElementById('pago-processing-text');
    if (card) card.classList.toggle('is-processing', !!active);
    if (proc) proc.hidden = !active;
    if (actions) actions.hidden = !!active;
    if (textEl && text) textEl.textContent = text;
  };

  window.simulateCardAuthorization = function simulateCardAuthorization(cardNumber) {
    const n = String(cardNumber || '').replace(/\D/g, '');
    if (!n) {
      return { ok: false, code: 'invalid_card', message: 'Número de tarjeta no válido.' };
    }
    if (n.endsWith('0002') || n === '4000000000000002') {
      return {
        ok: false,
        code: 'card_declined',
        message: 'La tarjeta fue rechazada por el emisor.',
      };
    }
    if (n.endsWith('9999')) {
      return {
        ok: false,
        code: 'insufficient_funds',
        message: 'Fondos insuficientes.',
      };
    }
    return { ok: true };
  };

  window.simulatePagoCardCharge = function simulatePagoCardCharge() {
    const validationMsg = validatePagoCardForm();
    if (validationMsg) {
      return Promise.reject(new Error(validationMsg));
    }
    const number = document.getElementById('pago-card-number')?.value || '';
    const auth = simulateCardAuthorization(number);
    if (!auth.ok) {
      setPagoProcessing(false);
      const formErr = document.getElementById('pago-form-error');
      if (formErr) {
        formErr.hidden = false;
        formErr.textContent = auth.message;
      }
      return Promise.reject(new Error(auth.message || 'card_declined'));
    }
    const steps = [
      { text: 'Validando tarjeta…', ms: 700 },
      { text: 'Autorizando pago…', ms: 900 },
      { text: 'Confirmando transacción…', ms: 650 },
    ];
    setPagoProcessing(true, steps[0].text);
    let chain = Promise.resolve();
    steps.forEach((step) => {
      chain = chain.then(() => new Promise((resolve) => {
        setPagoProcessing(true, step.text);
        setTimeout(resolve, step.ms);
      }));
    });
    return chain;
  };

  window.renderAuditTrail = function renderAuditTrail(entries, opts) {
    const o = opts || {};
    const rows = Array.isArray(entries) ? entries : [];
    if (!rows.length) {
      return `<p class="modal-sub">${o.empty || 'Sin eventos registrados en auditoría.'}</p>`;
    }
  const label = (action) => {
      const map = {
        update_payment: 'Pago actualizado',
        convert_request: 'Convertida a venta',
        return_request: 'Devolución',
        create_request: 'Solicitud creada',
        update_order: 'Pedido histórico editado',
        adjust_stock: 'Ajuste de stock',
        receive_po: 'Recepción OC',
        create_po: 'OC creada',
      };
      return map[action] || action || '—';
    };
    return `<div class="audit-trail">
      <div class="detail-label" style="margin-bottom:6px">${o.title || 'Historial de auditoría'}</div>
      <ul class="audit-trail-list">
        ${rows.map((e) => `<li>
          <span class="audit-trail-at">${window.formatBusinessDateTime ? window.formatBusinessDateTime(e.at) : ((e.at || '').replace('T', ' ').slice(0, 19) || '—')}</span>
          <strong>${label(e.action)}</strong>
          <span class="audit-trail-meta">${e.email || e.role || ''}${e.entity_id != null ? ` · #${e.entity_id}` : ''}</span>
        </li>`).join('')}
      </ul>
    </div>`;
  };

  window.fillPaymentMethodSelect = function fillPaymentMethodSelect(selectEl) {
    if (!selectEl) return;
    const opts = PAYMENT_METHOD_OPTIONS.card;
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

      const noticeOnly = opts.notice === true || (opts.confirmLabel || '').trim().toLowerCase() === 'cerrar';
      modal.classList.toggle('ops-confirm--wide', opts.wide === true);

      titleEl.textContent = opts.title || 'Confirmar';
      if (opts.html) msgEl.innerHTML = opts.html;
      else msgEl.textContent = opts.message || '';
      okBtn.textContent = opts.confirmLabel || 'Confirmar';
      cancelBtn.textContent = opts.cancelLabel || 'Cancelar';
      cancelBtn.hidden = noticeOnly;
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

  /** Aviso informativo: una sola acción inequívoca, Cerrar. */
  window.opsNotice = function opsNotice(opts) {
    const o = typeof opts === 'string' ? { message: opts } : (opts || {});
    return window.opsConfirm({ ...o, notice: true, confirmLabel: o.confirmLabel || 'Cerrar' });
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

  function enforceNumericMinimum(input, silent) {
    if (!(input instanceof HTMLInputElement) || input.type !== 'number') return;
    const minAttr = input.getAttribute('min');
    if (minAttr == null || minAttr === '') return;
    const min = Number(minAttr);
    if (!Number.isFinite(min)) return;
    const raw = String(input.value || '').trim();
    if (!raw) return;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < min) {
      input.value = String(min);
      if (!silent && typeof window.notifyWarn === 'function') {
        window.notifyWarn(`El valor mínimo permitido es ${min}.`);
      }
    }
  }

  document.addEventListener('input', (event) => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== 'number') return;
    if (String(input.value || '').startsWith('-')) enforceNumericMinimum(input, true);
  });

  document.addEventListener('blur', (event) => {
    enforceNumericMinimum(event.target, false);
  }, true);
})();
