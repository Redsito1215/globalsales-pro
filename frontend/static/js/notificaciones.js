/* Centro de notificaciones */
function notifTypeFrom(n) {
  const cat = String(n.category || '').toLowerCase();
  const subject = String(n.subject || '').toLowerCase();
  if (cat === 'compras' || subject.includes('oc #') || subject.includes('compra')) return 'compras';
  if (cat === 'soporte' || subject.includes('soporte') || subject.includes('mensaje')) return 'soporte';
  if (cat === 'solicitud' || subject.includes('solicitud') || n.request_id) return 'solicitud';
  return 'sistema';
}

function notifTypeMeta(type) {
  const map = {
    solicitud: { label: 'Solicitud', short: 'SOL' },
    soporte: { label: 'Soporte', short: 'SUP' },
    compras: { label: 'Compras', short: 'OC' },
    sistema: { label: 'Sistema', short: 'SYS' },
  };
  return map[type] || map.sistema;
}

async function refreshNotificationBadge() {
  if (!window._authUser) {
    const btn = document.getElementById('btn-notifications');
    if (btn) btn.hidden = true;
    document.getElementById('notif-nav-badge')?.setAttribute('hidden', '');
    return;
  }
  try {
    const r = await fetch(API + '/auth/notifications/pulse?after=0', { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) return;
    const n = data.unread || 0;
    const text = n > 99 ? '99+' : String(n);
    ['notif-badge', 'notif-nav-badge'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.hidden = n <= 0;
    });
    const btn = document.getElementById('btn-notifications');
    if (btn) btn.hidden = false;
  } catch { /* ignore */ }
}

function prependNotificationCard(n) {
  const list = document.getElementById('notificaciones-list');
  if (!list || !n) return;
  list.querySelector('.catalog-empty')?.remove();
  const type = notifTypeFrom(n);
  const metaT = notifTypeMeta(type);
  const unread = !n.read;
  const html = `
    <article class="notif-card notif-card--${type} ${n.read ? 'notif-card--read' : ''}" data-id="${n.notification_id}">
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
  list.insertAdjacentHTML('afterbegin', html);
  const meta = document.getElementById('notificaciones-meta');
  if (meta) {
    const cards = list.querySelectorAll('.notif-card');
    const unreadCount = [...cards].filter(c => !c.classList.contains('notif-card--read')).length;
    meta.textContent = `${unreadCount} sin leer · ${cards.length} en pantalla`;
  }
}

window.prependNotificationCard = prependNotificationCard;
window.notifTypeFrom = notifTypeFrom;

async function loadNotificacionesPage() {
  const list = document.getElementById('notificaciones-list');
  const meta = document.getElementById('notificaciones-meta');
  if (!list) return;
  if (!window._authUser) {
    list.innerHTML = '<p class="catalog-empty">Inicia sesión para ver notificaciones.</p>';
    return;
  }
  list.innerHTML = '<p class="catalog-empty">Cargando…</p>';
  const r = await fetch(API + '/auth/notifications?limit=50', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    list.innerHTML = `<p class="catalog-empty">${data.message || 'Error'}</p>`;
    return;
  }
  if (meta) meta.textContent = `${data.unread || 0} sin leer · ${data.total || 0} total`;
  const rows = data.notifications || [];
  if (!rows.length) {
    list.innerHTML = '<p class="catalog-empty">No tienes notificaciones.</p>';
    return;
  }
  list.innerHTML = rows.map(n => {
    const type = notifTypeFrom(n);
    const metaT = notifTypeMeta(type);
    const unread = !n.read;
    return `
    <article class="notif-card notif-card--${type} ${n.read ? 'notif-card--read' : ''}" data-id="${n.notification_id}">
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
  }).join('');
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
  loadNotificacionesPage();
}

document.addEventListener('click', async e => {
  const card = e.target.closest('.notif-card[data-id]');
  if (!card || card.classList.contains('notif-card--read')) return;
  if (e.target.closest('button')) return;
  const id = card.getAttribute('data-id');
  await fetch(`${API}/auth/notifications/${id}/read`, { method: 'PATCH', credentials: 'same-origin' });
  card.classList.add('notif-card--read');
  const tag = card.querySelector('.notif-tag');
  // remove "Sin leer" tag if present as second tag
  card.querySelectorAll('.notif-tag').forEach(t => {
    if (t.textContent === 'Sin leer') t.remove();
  });
  refreshNotificationBadge();
});
