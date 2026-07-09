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
  const pages = window._access?.pages || ['tienda'];
  return pages.includes(pageId);
}

function hasPermission(code) {
  if (window._authUser?.role === 'administrador') return true;
  return (window._access?.permissions || []).includes(code);
}

function defaultPageForUser() {
  const pages = window._access?.pages || ['tienda'];
  if (pages.includes('tienda')) return 'tienda';
  if (pages.includes('dashboard')) return 'dashboard';
  return pages[0] || 'tienda';
}

function applyNavAccess() {
  const pages = new Set(window._access?.pages || ['tienda']);
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.hidden = !pages.has(btn.getAttribute('data-page'));
  });
  document.querySelectorAll('.nav-section[data-nav-section]').forEach(sec => {
    const section = sec.getAttribute('data-nav-section');
    const items = document.querySelectorAll(`.nav-item[data-nav-section="${section}"]`);
    const anyVisible = [...items].some(b => !b.hidden);
    sec.hidden = !anyVisible;
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
