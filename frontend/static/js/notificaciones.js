/* Centro de notificaciones */
async function refreshNotificationBadge() {
  const badge = document.getElementById('notif-badge');
  const btn = document.getElementById('btn-notifications');
  if (!window._authUser) {
    if (btn) btn.hidden = true;
    return;
  }
  if (btn) btn.hidden = false;
  try {
    const r = await fetch(API + '/auth/notifications?limit=1', { credentials: 'same-origin' });
    const data = await r.json();
    if (!r.ok) return;
    const n = data.unread || 0;
    if (badge) {
      badge.textContent = n > 99 ? '99+' : String(n);
      badge.hidden = n <= 0;
    }
  } catch { /* ignore */ }
}

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
  list.innerHTML = rows.map(n => `
    <article class="notif-card ${n.read ? 'notif-card--read' : ''}" data-id="${n.notification_id}">
      <div class="notif-card-head">
        <strong>${n.subject}</strong>
        <span class="notif-date">${(n.created_at || '').slice(0, 16).replace('T', ' ')}</span>
      </div>
      <p class="notif-body">${(n.body || '').replace(/\n/g, '<br>')}</p>
      ${n.request_id ? `<button type="button" class="btn btn-ghost" style="font-size:11px;padding:4px 8px;margin-top:6px" onclick="openSolicitudDetail(${n.request_id})">Ver solicitud #${n.request_id}</button>` : ''}
    </article>`).join('');
  refreshNotificationBadge();
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
  refreshNotificationBadge();
});
