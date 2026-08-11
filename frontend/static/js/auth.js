/**
 * GLOBTRADE — Autenticación (sesión, registro, login).
 * Exploración libre; acciones sensibles requieren sesión (modelo Steam).
 */
(function (global) {
  const API = (global.GLOBTRADE_API || (global.location.origin + '/api'));

  let currentUser = null;

  function $(id) {
    return document.getElementById(id);
  }

  function fetchOpts(method, body) {
    const opts = {
      method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return opts;
  }

  async function apiAuth(path, method, body) {
    const r = await fetch(API + '/auth' + path, fetchOpts(method, body));
    let data = {};
    try {
      data = await r.json();
    } catch (_) {
      data = { status: 'error', message: r.statusText };
    }
    return { ok: r.ok, status: r.status, data };
  }

  function isAuthenticated() {
    return !!currentUser;
  }

  function isAdmin() {
    return currentUser && currentUser.role === 'administrador';
  }

  function showFieldErrors(errors, prefix) {
    Object.keys(errors || {}).forEach((key) => {
      const el = $(prefix + key);
      if (el) {
        el.textContent = errors[key];
        el.style.display = 'block';
      }
    });
  }

  function clearFieldErrors(prefix, fields) {
    fields.forEach((key) => {
      const el = $(prefix + key);
      if (el) {
        el.textContent = '';
        el.style.display = 'none';
      }
    });
  }

  function updateTopbar() {
    const guest = $('auth-guest');
    const user = $('auth-user');
    const nameEl = $('auth-user-name');
    const roleEl = $('auth-user-role');
    if (!guest || !user) return;

    if (currentUser) {
      guest.style.display = 'none';
      user.style.display = 'flex';
      if (nameEl) nameEl.textContent = currentUser.name || currentUser.email;
      if (roleEl) {
        roleEl.textContent =
          currentUser.role === 'administrador' ? 'Administrador' : 'Analista';
      }
    } else {
      guest.style.display = 'flex';
      user.style.display = 'none';
    }
  }

  function openModal(id) {
    const m = $(id);
    if (m) m.classList.add('open');
  }

  function closeModal(id) {
    const m = $(id);
    if (m) m.classList.remove('open');
  }

  function closeAllModals() {
    document.querySelectorAll('.auth-modal').forEach((m) => m.classList.remove('open'));
  }

  function showAuthMessage(elId, text, isError) {
    const el = $(elId);
    if (!el) return;
    el.textContent = text || '';
    el.style.color = isError ? 'var(--danger)' : 'var(--accent)';
    el.style.display = text ? 'block' : 'none';
  }

  async function refreshSession() {
    try {
      const r = await fetch(API + '/auth/me', { credentials: 'same-origin' });
      const data = await r.json();
      if (data.authenticated && data.user) {
        currentUser = data.user;
      } else {
        currentUser = null;
      }
    } catch (_) {
      currentUser = null;
    }
    updateTopbar();
    return currentUser;
  }

  /**
   * Si no hay sesión, abre login y devuelve false.
   * @param {object} opts - { admin: bool, message: string }
   */
  function requireAuth(opts) {
    opts = opts || {};
    if (opts.admin && (!currentUser || currentUser.role !== 'administrador')) {
      if (!currentUser) {
        showAuthMessage('login-form-msg', opts.message || 'Inicia sesión para continuar.', true);
        openModal('modal-login');
        return false;
      }
      notifyWarn('Solo administradores pueden realizar esta acción.');
      return false;
    }
    if (!currentUser) {
      showAuthMessage('login-form-msg', opts.message || 'Inicia sesión para continuar.', true);
      openModal('modal-login');
      return false;
    }
    return true;
  }

  async function register() {
    clearFieldErrors('reg-err-', ['email', 'name', 'password', 'password_confirm']);
    showAuthMessage('register-form-msg', '', false);

    const payload = {
      email: ($('reg-email') || {}).value,
      name: ($('reg-name') || {}).value,
      password: ($('reg-password') || {}).value,
      password_confirm: ($('reg-password2') || {}).value,
    };

    const { ok, data } = await apiAuth('/register', 'POST', payload);
    if (!ok) {
      showFieldErrors(data.errors, 'reg-err-');
      showAuthMessage('register-form-msg', data.message || 'No se pudo crear la cuenta.', true);
      return;
    }

    currentUser = data.user;
    updateTopbar();
    closeAllModals();
    notifyOk(data.message || 'Cuenta creada. ¡Bienvenido!');
  }

  async function login() {
    clearFieldErrors('login-err-', ['email', 'password']);
    showAuthMessage('login-form-msg', '', false);

    const payload = {
      email: ($('login-email') || {}).value,
      password: ($('login-password') || {}).value,
    };

    const { ok, data } = await apiAuth('/login', 'POST', payload);
    if (!ok) {
      showFieldErrors(data.errors, 'login-err-');
      showAuthMessage('login-form-msg', data.message || 'No se pudo iniciar sesión.', true);
      return;
    }

    currentUser = data.user;
    updateTopbar();
    closeAllModals();
  }

  async function logout() {
    await apiAuth('/logout', 'POST');
    currentUser = null;
    updateTopbar();
  }

  function bindUi() {
    $('btn-open-login')?.addEventListener('click', () => {
      showAuthMessage('login-form-msg', '', false);
      openModal('modal-login');
    });
    $('btn-open-register')?.addEventListener('click', () => {
      showAuthMessage('register-form-msg', '', false);
      openModal('modal-register');
    });
    $('btn-logout')?.addEventListener('click', logout);
    $('btn-login-submit')?.addEventListener('click', (e) => {
      e.preventDefault();
      login();
    });
    $('btn-register-submit')?.addEventListener('click', (e) => {
      e.preventDefault();
      register();
    });
    $('link-to-register')?.addEventListener('click', (e) => {
      e.preventDefault();
      closeModal('modal-login');
      openModal('modal-register');
    });
    $('link-to-login')?.addEventListener('click', (e) => {
      e.preventDefault();
      closeModal('modal-register');
      openModal('modal-login');
    });

    document.querySelectorAll('[data-auth-close]').forEach((btn) => {
      btn.addEventListener('click', closeAllModals);
    });
    document.querySelectorAll('.auth-modal').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeAllModals();
      });
    });

    ['login-email', 'login-password'].forEach((id) => {
      $(id)?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') login();
      });
    });
  }

  global.GlobtradeAuth = {
    API,
    refreshSession,
    requireAuth,
    isAuthenticated,
    isAdmin,
    getUser: () => currentUser,
    fetchWithAuth: async (path, options) => {
      const o = options || {};
      const authOpts = o.auth || {};
      const { auth: _a, ...rest } = o;
      if (!requireAuth(authOpts)) {
        return { ok: false, status: 401, data: { status: 'error', code: 'auth_required' } };
      }
      const opts = Object.assign(
        { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } },
        rest
      );
      const r = await fetch(API + path, opts);
      let data = {};
      try {
        data = await r.json();
      } catch (_) {
        data = {};
      }
      if (r.status === 401 && data.code === 'auth_required') {
        currentUser = null;
        updateTopbar();
        requireAuth({ message: data.message });
      }
      return { ok: r.ok, status: r.status, data };
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    bindUi();
    refreshSession();
  });
})(window);
