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
  const pages = window._access?.pages || ['tienda'];
  const role = window._authUser?.role || window._access?.role || null;
  const pick = (id) => (pages.includes(id) || role === 'administrador' ? id : null);

  if (role === 'cliente') return pick('tienda') || pages[0] || 'tienda';
  if (role === 'vendedor') return pick('ventas') || pick('tienda') || pages[0] || 'tienda';
  if (role === 'analista') return pick('dashboard') || pick('decisiones') || pages[0] || 'tienda';
  if (role === 'administrador') return 'dashboard';

  if (pick('tienda')) return 'tienda';
  if (pick('dashboard')) return 'dashboard';
  return pages[0] || 'tienda';
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
  const pages = new Set(window._access?.pages || ['tienda']);
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

  const ordersBtn = document.getElementById('shop-hero-orders-btn');
  if (ordersBtn) ordersBtn.hidden = !canAccessPage('mis-pedidos');
}

function guardPageAccess(pageId) {
  if (canAccessPage(pageId)) return true;
  const fallback = defaultPageForUser();
  const btn = document.querySelector(`.nav-item[data-page="${fallback}"]`);
  showPage(fallback, btn);
  return false;
}
