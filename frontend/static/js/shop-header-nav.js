/* Menú header tienda — secciones con dropdown por rol */
const SHOP_NAV_SECTIONS = [
  {
    id: 'ops',
    label: 'Operativo',
    items: [
      { page: 'tienda', label: 'Tienda' },
      { page: 'mis-pedidos', label: 'Mis pedidos' },
      { page: 'ventas', label: 'Pedidos y ventas' },
      { page: 'compras', label: 'Compras e inventario' },
      { page: 'notificaciones', label: 'Notificaciones' },
      { page: 'soporte', label: 'Soporte' },
    ],
  },
  {
    id: 'q2',
    label: 'Estratégico',
    items: [
      { page: 'dashboard', label: 'Resumen ejecutivo' },
      { page: 'decisiones', label: 'Centro de decisiones' },
      { page: 'reportes-compuestos', label: 'Informes gerenciales' },
      { page: 'trends', label: 'Tendencia ejecutiva' },
      { page: 'regions', label: 'Mercado por región' },
    ],
  },
  {
    id: 'gestion',
    label: 'Táctico',
    items: [
      { page: 'reportes', label: 'Informes operativos' },
      { page: 'orders', label: 'Explorar ventas' },
      { page: 'catalogo', label: 'Catálogo analítico' },
      { page: 'export', label: 'Descargar datos' },
      { gestion: 'dim_region', label: 'Regiones' },
      { gestion: 'dim_pais', label: 'Países' },
      { gestion: 'dim_categoria', label: 'Categorías' },
      { gestion: 'dim_producto', label: 'Productos' },
      { gestion: 'dim_canal', label: 'Canales' },
      { gestion: 'dim_prioridad', label: 'Prioridades' },
      { gestion: 'dim_cliente', label: 'Clientes' },
    ],
  },
  {
    id: 'admin',
    label: 'Administración',
    items: [
      { page: 'company', label: 'Empresa' },
      { page: 'schema', label: 'Modelo de datos' },
      { page: 'load', label: 'Carga de datos' },
      { page: 'audit', label: 'Auditoría' },
      { page: 'roles-admin', label: 'Roles y usuarios', perm: 'users.manage' },
    ],
  },
];

function shopNavItemVisible(item) {
  if (item.perm && typeof hasPermission === 'function' && !hasPermission(item.perm)) return false;
  if (item.gestion) return typeof canAccessPage === 'function' && canAccessPage('gestion');
  return typeof canAccessPage === 'function' && canAccessPage(item.page);
}

function shouldFlattenShopNav() {
  return window._authUser?.role === 'cliente';
}

function collectVisibleShopNavItems() {
  const items = [];
  SHOP_NAV_SECTIONS.forEach((section) => {
    section.items.filter(shopNavItemVisible).forEach((item) => items.push(item));
  });
  return items;
}

function shopNavItemAttrs(item) {
  const page = item.page ? ` data-shop-page="${item.page}"` : '';
  const gestion = item.gestion ? ` data-shop-gestion="${item.gestion}"` : '';
  const report = item.report ? ` data-shop-report="${item.report}"` : '';
  return { page, gestion, report };
}

function renderShopNavFlatItems(items) {
  return items
    .map((item) => {
      const { page, gestion, report } = shopNavItemAttrs(item);
      return `
        <div class="shop-nav-group shop-nav-group--direct">
          <button type="button" class="shop-nav-group-toggle shop-nav-direct-link"${page}${gestion}${report}>
            <span>${item.label}</span>
          </button>
        </div>`;
    })
    .join('');
}

function openShopNavGroup(group) {
  if (!group) return;
  const toggle = group.querySelector('.shop-nav-group-toggle');
  group.classList.add('is-open');
  if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

function closeShopNavGroups() {
  document.querySelectorAll('.shop-nav-group.is-open').forEach((group) => {
    group.classList.remove('is-open', 'is-pinned');
    const toggle = group.querySelector('.shop-nav-group-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  });
}

function toggleShopNavGroup(btn) {
  const group = btn?.closest?.('.shop-nav-group');
  if (!group) return;
  const isDesktop = window.matchMedia('(min-width: 901px)').matches;

  if (isDesktop) {
    const isOpen = group.classList.contains('is-open');
    const isPinned = group.classList.contains('is-pinned');
    if (isOpen && isPinned) {
      group.classList.remove('is-open', 'is-pinned');
      btn.setAttribute('aria-expanded', 'false');
      return;
    }
    closeShopNavGroups();
    openShopNavGroup(group);
    group.classList.add('is-pinned');
    return;
  }

  const willOpen = !group.classList.contains('is-open');
  closeShopNavGroups();
  if (willOpen) openShopNavGroup(group);
}

function bindShopNavHover() {
  const nav = document.getElementById('shop-madson-nav');
  if (!nav || nav.dataset.hoverBound === '1') return;
  nav.dataset.hoverBound = '1';
  const hoverCloseDelayMs = 3000;

  nav.querySelectorAll('.shop-nav-group').forEach((group) => {
    let closeTimer = null;

    group.addEventListener('mouseenter', () => {
      if (!window.matchMedia('(min-width: 901px)').matches) return;
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      closeShopNavGroups();
      openShopNavGroup(group);
    });

    group.addEventListener('mouseleave', () => {
      if (!window.matchMedia('(min-width: 901px)').matches) return;
      if (group.classList.contains('is-pinned')) return;
      closeTimer = setTimeout(() => {
        if (group.classList.contains('is-pinned')) return;
        group.classList.remove('is-open');
        const toggle = group.querySelector('.shop-nav-group-toggle');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
      }, hoverCloseDelayMs);
    });
  });
}

function navigateShopNavItem(item) {
  if (typeof closeShopNavDropdown === 'function') closeShopNavDropdown();
  closeShopNavGroups();
  if (item.gestion) {
    const sideBtn = document.querySelector(`.nav-item[data-gestion-table="${item.gestion}"]`);
    if (typeof showGestion === 'function') showGestion(item.gestion, sideBtn);
    return;
  }
  if (!item.page) return;
  const sideBtn = document.querySelector(`.nav-item[data-page="${item.page}"]`);
  if (item.report && typeof openStrategicReport === 'function') {
    openStrategicReport(item.report, sideBtn);
    return;
  }
  const pageOpts = item.page === 'tienda' ? { tiendaMode: 'catalog' } : {};
  if (typeof showPage === 'function') showPage(item.page, sideBtn, pageOpts);
}

function renderShopHeaderNav() {
  const nav = document.getElementById('shop-madson-nav');
  if (!nav) return;

  const loggedIn = !!window._authUser;
  const headerAuth = document.getElementById('shop-header-auth');
  if (headerAuth) headerAuth.hidden = !loggedIn;
  const headerLogin = document.getElementById('shop-header-login');
  if (headerLogin) headerLogin.hidden = loggedIn;

  const parts = [];

  if (!loggedIn) {
    parts.push(`
      <div class="shop-nav-guest">
        <button type="button" class="shop-nav-guest-link" onclick="showPage('tienda', document.querySelector('[data-page=tienda]'), { tiendaMode: 'catalog' })">Tienda</button>
      </div>
      <div class="shop-madson-nav-auth" id="shop-nav-auth-guest">
        <button type="button" class="shop-madson-nav-auth-btn" onclick="openRegisterModal()">Crear cuenta</button>
        <button type="button" class="shop-madson-nav-auth-btn shop-madson-nav-auth-btn--primary" onclick="openLoginModal()">Iniciar sesión</button>
      </div>`);
  } else if (shouldFlattenShopNav()) {
    const flatItems = collectVisibleShopNavItems();
    if (flatItems.length) parts.push(renderShopNavFlatItems(flatItems));
    parts.push(`
      <div class="shop-madson-nav-auth" id="shop-nav-auth-user">
        <button type="button" class="shop-madson-nav-auth-btn" onclick="openProfileModal()">Mi perfil</button>
        <button type="button" class="shop-madson-nav-auth-btn" onclick="logout()">Cerrar sesión</button>
      </div>`);
  } else {
    SHOP_NAV_SECTIONS.forEach((section) => {
      const visibleItems = section.items.filter(shopNavItemVisible);
      if (!visibleItems.length) return;
      const itemsHtml = visibleItems
        .map((item) => {
          const { page, gestion, report } = shopNavItemAttrs(item);
          return `<button type="button" class="shop-nav-dropdown-item"${page}${gestion}${report}>${item.label}</button>`;
        })
        .join('');
      parts.push(`
        <div class="shop-nav-group" data-shop-nav-section="${section.id}">
          <button type="button" class="shop-nav-group-toggle" aria-expanded="false" onclick="toggleShopNavGroup(this)">
            <span>${section.label}</span>
            <svg class="shop-nav-chevron" viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 8l5 5 5-5"/></svg>
          </button>
          <div class="shop-nav-dropdown">${itemsHtml}</div>
        </div>`);
    });
    parts.push(`
      <div class="shop-madson-nav-auth" id="shop-nav-auth-user">
        <button type="button" class="shop-madson-nav-auth-btn" onclick="openProfileModal()">Mi perfil</button>
        <button type="button" class="shop-madson-nav-auth-btn" onclick="logout()">Cerrar sesión</button>
      </div>`);
  }

  nav.innerHTML = parts.join('');

  nav.onclick = (event) => {
    const btn = event.target.closest('.shop-nav-dropdown-item, .shop-nav-direct-link');
    if (!btn) return;
    event.stopPropagation();
    const page = btn.getAttribute('data-shop-page') || '';
    const gestion = btn.getAttribute('data-shop-gestion') || '';
    const report = btn.getAttribute('data-shop-report') || '';
    navigateShopNavItem({
      page: page || undefined,
      gestion: gestion || undefined,
      report: report || undefined,
    });
  };

  bindShopNavHover();
}

document.addEventListener('click', (event) => {
  const isDesktop = window.matchMedia('(min-width: 901px)').matches;
  if (isDesktop) {
    if (!event.target.closest('.shop-nav-group')) {
      closeShopNavGroups();
    }
    return;
  }
  if (!event.target.closest('.shop-nav-group') && !event.target.closest('#shop-panel-toggle')) {
    closeShopNavGroups();
  }
});
