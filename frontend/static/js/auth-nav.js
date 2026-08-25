/* Navegación y permisos por rol */
window._access = { pages: ['tienda'], permissions: [], role: null };

function setAccess(access) {
  if (!access) return;
  window._access = {
    pages: access.pages || ['tienda'],
    permissions: access.permissions || [],
    role: access.role || window._authUser?.role || null,
    page_catalog: access.page_catalog || window._access?.page_catalog || {},
    permission_catalog: access.permission_catalog || window._access?.permission_catalog || {},
  };
}

function canAccessPage(pageId) {
  if (pageId === 'datos') pageId = 'gestion';
  if (!window._authUser) return pageId === 'tienda';
  if (window._authUser?.role === 'administrador' || window._access?.role === 'administrador') {
    return true;
  }
  const pages = window._access?.pages || ['tienda'];
  return pages.includes(pageId);
}

function hasPermission(code) {
  if (window._authUser?.role === 'administrador' || window._access?.role === 'administrador') return true;
  return (window._access?.permissions || []).includes(code);
}

function defaultPageForUser() {
  if (!window._authUser) return 'tienda';
  const pages = window._access?.pages || ['tienda'];
  const role = window._authUser?.role || window._access?.role || null;
  const pick = (id) => (pages.includes(id) || role === 'administrador' ? id : null);

  // Inicio unificado: Tienda (diseño storefront) si el rol puede verla
  if (pick('tienda')) return 'tienda';

  if (role === 'cliente') return pages[0] || 'tienda';
  if (role === 'vendedor') return pick('ventas') || pages[0] || 'tienda';
  if (role === 'analista') return pick('dashboard') || pick('decisiones') || pages[0] || 'tienda';

  if (pick('dashboard')) return 'dashboard';
  return pages[0] || 'tienda';
}

function pageAfterAuth() {
  const currentId = document.querySelector('.page.active')?.id?.replace('page-', '');
  if (currentId && canAccessPage(currentId)) return currentId;
  return defaultPageForUser();
}

function toggleNavGroup(btn) {
  const group = btn?.closest?.('.nav-folder') || btn?.closest?.('.nav-group');
  if (!group) return;
  const open = !group.classList.contains('is-open');
  group.classList.toggle('is-open', open);
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function openNavGroupForPage(pageId) {
  const item = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  const group = item?.closest?.('.nav-folder') || item?.closest?.('.nav-group');
  if (!group) return;
  group.classList.add('is-open');
  const toggle = group.querySelector('.nav-folder-toggle, .nav-group-toggle');
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

function applyNavAccess() {
  const role = window._authUser?.role || window._access?.role || null;
  const loggedIn = !!window._authUser;
  // Sin sesión: solo Tienda (nada de Administración ni otras secciones)
  const pages = new Set(
    !loggedIn ? ['tienda'] : (window._access?.pages || ['tienda'])
  );
  const isAdmin = role === 'administrador';
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    const id = btn.getAttribute('data-page');
    btn.hidden = isAdmin ? false : !pages.has(id);
  });

  document.querySelectorAll('.nav-block[data-nav-section]').forEach(block => {
    const items = block.querySelectorAll('.nav-item[data-page]');
    const anyVisible = [...items].some(b => !b.hidden);
    block.hidden = !anyVisible;
  });

  // Visitante: sin títulos de carpeta; solo el ítem Tienda
  document.querySelectorAll('.nav-folder-toggle').forEach((toggle) => {
    toggle.hidden = !loggedIn;
  });
  if (!loggedIn) {
    document.querySelectorAll('.nav-folder').forEach((folder) => {
      folder.classList.add('is-open');
      const t = folder.querySelector('.nav-folder-toggle');
      if (t) t.setAttribute('aria-expanded', 'true');
    });
  }

  const ordersBtn = document.getElementById('shop-hero-orders-btn');
  if (ordersBtn) ordersBtn.hidden = !canAccessPage('mis-pedidos');

  if (typeof renderShopHeaderNav === 'function') renderShopHeaderNav();

  applyPermissionUi();
}

function applyPermissionUi() {
  document.querySelectorAll('[data-require-perm]').forEach(el => {
    const code = el.getAttribute('data-require-perm');
    const allowed = !code || hasPermission(code);
    el.hidden = !allowed;
    if ('disabled' in el) el.disabled = !allowed;
    el.setAttribute('aria-hidden', allowed ? 'false' : 'true');
  });
}

function guardPageAccess(pageId) {
  if (canAccessPage(pageId)) return true;
  const fallback = defaultPageForUser();
  const btn = document.querySelector(`.nav-item[data-page="${fallback}"]`);
  showPage(fallback, btn);
  return false;
}
