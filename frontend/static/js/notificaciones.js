/* Centro de notificaciones */
const NOTIF_FILTER_OPTIONS = [
  { id: 'all', label: 'Todas' },
  { id: 'solicitud', label: 'Solicitud' },
  { id: 'pago', label: 'Pagos' },
  { id: 'soporte', label: 'Soporte' },
  { id: 'compras', label: 'Compras' },
  { id: 'sistema', label: 'Sistema' },
];

let _notifRows = [];
let _notifCategoryFilter = 'all';

function notifTypeFrom(n) {
  const cat = String(n.category || '').toLowerCase();
  const subject = String(n.subject || '').toLowerCase();
  if (cat === 'compras' || subject.includes('oc #') || subject.includes('compra')) return 'compras';
  if (cat === 'pago' || subject.includes('pago')) return 'pago';
  if (cat === 'soporte' || subject.includes('soporte') || subject.includes('mensaje')) return 'soporte';
  if (cat === 'solicitud' || subject.includes('solicitud') || n.request_id) return 'solicitud';
  return 'sistema';
}

function notifTypeMeta(type) {
  const map = {
    solicitud: { label: 'Solicitud', short: 'SOL' },
    soporte: { label: 'Soporte', short: 'SUP' },
    compras: { label: 'Compras', short: 'OC' },
    pago: { label: 'Pagos', short: '$' },
    sistema: { label: 'Sistema', short: 'SYS' },
  };
  return map[type] || map.sistema;
}

function filteredNotifRows(rows) {
  const term = String(document.getElementById('notificaciones-q')?.value || '').trim().toLowerCase();
  const unreadOnly = !!document.getElementById('notificaciones-unread')?.checked;
  return rows.filter(n => {
    if (_notifCategoryFilter !== 'all' && notifTypeFrom(n) !== _notifCategoryFilter) return false;
    if (unreadOnly && n.read) return false;
    if (term && !`${n.subject || ''} ${n.body || ''}`.toLowerCase().includes(term)) return false;
    return true;
  });
}

function notifCardHtml(n) {
  const type = notifTypeFrom(n);
  const metaT = notifTypeMeta(type);
  const unread = !n.read;
  return `
    <article class="notif-card notif-card--${type} ${n.read ? 'notif-card--read' : ''}" data-id="${n.notification_id}" data-type="${type}">
      <div class="notif-icon" aria-hidden="true">${metaT.short}</div>
      <div class="notif-card-main">
        <div class="notif-tags">
          <span class="notif-tag">${metaT.label}</span>
          ${unread ? '<span class="notif-tag">Sin leer</span>' : ''}
        </div>
        <div class="notif-card-head">
          <strong>${n.subject || 'Aviso'}</strong>
          <span class="notif-date">${(n.created_at || '').slice(0, 16).replace('T', ' ')}</span>
        </div>
        <p class="notif-body">${(n.body || '').replace(/\n/g, '<br>')}</p>
        <div class="notif-actions">${notifActionsHtml(n, type)}</div>
      </div>
    </article>`;
}

function updateNotificacionesMeta(rows) {
  const meta = document.getElementById('notificaciones-meta');
  if (!meta) return;
  const unreadFiltered = rows.filter(n => !n.read).length;
  const totalLoaded = _notifRows.length;
  if (_notifCategoryFilter === 'all') {
    meta.textContent = `${unreadFiltered} sin leer · ${rows.length} en pantalla`;
    return;
  }
  const label = notifTypeMeta(_notifCategoryFilter).label;
  meta.textContent = `${unreadFiltered} sin leer · ${rows.length} ${label.toLowerCase()} · ${totalLoaded} total`;
}

function renderNotificacionesFilters() {
  const el = document.getElementById('notificaciones-filters');
  if (!el) return;
  el.innerHTML = NOTIF_FILTER_OPTIONS.map(opt => {
    const count = opt.id === 'all'
      ? _notifRows.length
      : _notifRows.filter(n => notifTypeFrom(n) === opt.id).length;
    const active = _notifCategoryFilter === opt.id;
    return `<button type="button" class="notif-filter-btn${active ? ' is-active' : ''}" data-cat="${opt.id}" onclick="setNotificacionCategoryFilter('${opt.id}')">${opt.label}<span class="notif-filter-count">${count}</span></button>`;
  }).join('');
}

function renderNotificacionesList() {
  const list = document.getElementById('notificaciones-list');
  if (!list) return;
  const rows = filteredNotifRows(_notifRows);
  updateNotificacionesMeta(rows);
  if (!_notifRows.length) {
    list.innerHTML = '<p class="catalog-empty">No tienes notificaciones.</p>';
    return;
  }
  if (!rows.length) {
    list.innerHTML = '<p class="catalog-empty">No hay notificaciones en esta categoría.</p>';
    return;
  }
  list.innerHTML = rows.map(notifCardHtml).join('');
}

function setNotificacionCategoryFilter(cat) {
  _notifCategoryFilter = cat || 'all';
  renderNotificacionesFilters();
  renderNotificacionesList();
}

async function refreshNotificationBadge() {
  if (!window._authUser) {
    const btn = document.getElementById('btn-notifications');
    if (btn) btn.hidden = true;
    document.getElementById('notif-nav-badge')?.setAttribute('hidden', '');
    document.getElementById('shop-header-notif-badge')?.setAttribute('hidden', '');
    document.getElementById('shop-header-notifications')?.setAttribute('hidden', '');
    return;
  }
  try {
    const r = await fetch(API + '/auth/notifications/pulse?after=0', { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) return;
    const n = data.unread || 0;
    const text = n > 99 ? '99+' : String(n);
    ['notif-badge', 'notif-nav-badge', 'shop-header-notif-badge'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.hidden = n <= 0;
    });
    const btn = document.getElementById('btn-notifications');
    const shopNotif = document.getElementById('shop-header-notifications');
    if (btn) btn.hidden = false;
    if (shopNotif && typeof canAccessPage === 'function' && canAccessPage('notificaciones')) {
      shopNotif.hidden = false;
      shopNotif.classList.toggle('shop-madson-notif-btn--has-unread', n > 0);
    }
  } catch { /* ignore */ }
}

function prependNotificationCard(n) {
  const list = document.getElementById('notificaciones-list');
  if (!list || !n) return;
  _notifRows = [n, ..._notifRows.filter(row => row.notification_id !== n.notification_id)];
  renderNotificacionesFilters();
  const type = notifTypeFrom(n);
  const matchesFilter = _notifCategoryFilter === 'all' || _notifCategoryFilter === type;
  if (matchesFilter) {
    list.querySelector('.catalog-empty')?.remove();
    list.insertAdjacentHTML('afterbegin', notifCardHtml(n));
  }
  updateNotificacionesMeta(filteredNotifRows(_notifRows));
}

window.prependNotificationCard = prependNotificationCard;
window.notifTypeFrom = notifTypeFrom;
window.setNotificacionCategoryFilter = setNotificacionCategoryFilter;

async function loadNotificacionesPage() {
  const list = document.getElementById('notificaciones-list');
  if (!list) return;
  if (!window._authUser) {
    _notifRows = [];
    renderNotificacionesFilters();
    list.innerHTML = '<p class="catalog-empty">Inicia sesión para ver notificaciones.</p>';
    return;
  }
  list.innerHTML = '<p class="catalog-empty">Cargando…</p>';
  const r = await fetch(API + '/auth/notifications?limit=200', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    _notifRows = [];
    renderNotificacionesFilters();
    list.innerHTML = `<p class="catalog-empty">${data.message || 'Error al procesar'}</p>`;
    return;
  }
  _notifRows = data.notifications || [];
  renderNotificacionesFilters();
  renderNotificacionesList();
  refreshNotificationBadge();
}

function notifActionsHtml(n, type) {
  const parts = [];
  if (n.request_id) {
    parts.push(`<button type="button" class="btn btn-primary btn-sm" onclick="openSolicitudDetail(${n.request_id})">Ver solicitud #${n.request_id}</button>`);
  }
  const poId = n.meta && n.meta.po_id != null ? Number(n.meta.po_id) : null;
  if ((type === 'compras' || poId) && typeof openComprasPo === 'function') {
    parts.push(`<button type="button" class="btn btn-ghost btn-sm" onclick="openComprasPo(${poId || 'null'})">Ir a Compras${poId ? ' · OC #' + poId : ''}</button>`);
  } else if (type === 'compras' && typeof showPage === 'function') {
    parts.push(`<button type="button" class="btn btn-ghost btn-sm" onclick="showPage('compras')">Ir a Compras</button>`);
  }
  if (type === 'soporte' && typeof showPage === 'function') {
    parts.push(`<button type="button" class="btn btn-ghost btn-sm" onclick="showPage('soporte')">Abrir soporte</button>`);
  }
  return parts.join(' ');
}

async function markAllNotificationsRead() {
  await fetch(API + '/auth/notifications/read-all', { method: 'POST', credentials: 'same-origin' });
  _notifRows = _notifRows.map(n => ({ ...n, read: true }));
  renderNotificacionesList();
  refreshNotificationBadge();
}

document.addEventListener('click', async e => {
  const card = e.target.closest('.notif-card[data-id]');
  if (!card || card.classList.contains('notif-card--read')) return;
  if (e.target.closest('button')) return;
  const id = Number(card.getAttribute('data-id'));
  await fetch(`${API}/auth/notifications/${id}/read`, { method: 'PATCH', credentials: 'same-origin' });
  card.classList.add('notif-card--read');
  _notifRows = _notifRows.map(n => (n.notification_id === id ? { ...n, read: true } : n));
  card.querySelectorAll('.notif-tag').forEach(t => {
    if (t.textContent === 'Sin leer') t.remove();
  });
  updateNotificacionesMeta(filteredNotifRows(_notifRows));
  refreshNotificationBadge();
});
