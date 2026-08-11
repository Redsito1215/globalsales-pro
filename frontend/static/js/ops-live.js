/* Pulse en vivo — toasts, sonido y UX sin recargar páginas */
(function () {
  const INBOX_POLL_MS = 5000;
  const ACCESS_POLL_MS = 60000;
  const STALE_CHECK_MS = 120000;
  const STALE_SYNC_COOLDOWN_MS = 300000;
  const SOUND_KEY = 'gt-notif-sound';
  const STAFF_ROLES = new Set(['administrador', 'vendedor', 'analista']);

  let inboxTimer = null;
  let accessTimer = null;
  let staleTimer = null;
  let busyInbox = false;
  let busyAccess = false;
  let busyStale = false;
  let lastNotificationId = 0;
  let lastAccessSig = '';
  let lastStaleSyncAt = 0;
  let inboxSeeded = false;

  function apiBase() {
    return (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
  }

  function accessSignature(user, access) {
    if (!user) return 'guest';
    const a = access || window._access || {};
    const pages = [...(a.pages || [])].sort().join(',');
    const perms = [...(a.permissions || [])].sort().join(',');
    return `${user.role || ''}|${pages}|${perms}`;
  }

  function activePageId() {
    const active = document.querySelector('.page.active');
    return active?.id?.replace('page-', '') || null;
  }

  function isUserEditing() {
    const el = document.activeElement;
    if (!el) return false;
    const tag = el.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
      const type = (el.type || '').toLowerCase();
      if (type === 'checkbox' || type === 'radio' || type === 'button' || type === 'submit') return false;
      return true;
    }
    return !!el.isContentEditable;
  }

  function opsUxDefaultSoundForRole() {
    const role = window._authUser?.role;
    return STAFF_ROLES.has(role);
  }

  function opsUxSoundEnabled() {
    const stored = localStorage.getItem(SOUND_KEY);
    if (stored === '0') return false;
    if (stored === '1') return true;
    return opsUxDefaultSoundForRole();
  }

  function opsUxSetNotifSound(enabled) {
    localStorage.setItem(SOUND_KEY, enabled ? '1' : '0');
  }

  function playNotifSound() {
    if (!opsUxSoundEnabled()) return;
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(740, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(988, ctx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.07, ctx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.28);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.3);
      setTimeout(() => ctx.close().catch(() => {}), 400);
    } catch (_) { /* sin audio */ }
  }

  function setLiveIndicator(on) {
    const dot = document.getElementById('notif-live-dot');
    if (dot) {
      dot.hidden = !on;
      dot.setAttribute('aria-hidden', on ? 'false' : 'true');
    }
  }

  function popBadges() {
    document.querySelectorAll('#notif-badge, #notif-nav-badge').forEach(el => {
      el.classList.remove('notif-badge--pop');
      void el.offsetWidth;
      el.classList.add('notif-badge--pop');
    });
  }

  function updateBadges(unread) {
    const text = unread > 99 ? '99+' : String(unread || 0);
    ['notif-badge', 'notif-nav-badge'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.hidden = unread <= 0;
    });
    const btn = document.getElementById('btn-notifications');
    if (btn) {
      if (window._authUser) btn.hidden = false;
      btn.classList.toggle('notif-btn--has-unread', unread > 0);
    }
  }

  function notifKind(n) {
    if (typeof notifTypeFrom === 'function') return notifTypeFrom(n);
    const cat = String(n.category || '').toLowerCase();
    if (cat.includes('soporte')) return 'soporte';
    if (cat.includes('comercial') || cat.includes('pedido') || n.request_id) return 'solicitud';
    if (cat.includes('compras')) return 'compras';
    return 'sistema';
  }

  function toastForNotification(n) {
    if (typeof opsToast !== 'function') return;
    const kind = notifKind(n);
    const toastType = kind === 'soporte' ? 'info' : (kind === 'compras' ? 'warn' : 'ok');
    const bodyLine = String(n.body || '').split('\n').find(Boolean) || '';
    const message = bodyLine ? `${n.subject || 'Nueva notificación'} — ${bodyLine}` : (n.subject || 'Nueva notificación');

    const action = () => {
      if (n.request_id && typeof openSolicitudDetail === 'function') {
        openSolicitudDetail(n.request_id);
        return;
      }
      if (kind === 'soporte') {
        const thread = n.meta?.thread_email;
        if (typeof showPage === 'function') {
          showPage('soporte', document.querySelector('[data-page=soporte]'));
        }
        if (thread && typeof openSoporteThread === 'function') {
          setTimeout(() => openSoporteThread(thread), 120);
        }
        return;
      }
      if (kind === 'compras' && typeof showPage === 'function') {
        showPage('compras', document.querySelector('[data-page=compras]'));
        return;
      }
      if (typeof showPage === 'function') {
        showPage('notificaciones', document.querySelector('[data-page=notificaciones]'));
      }
    };

    opsToast(message, toastType, {
      actionLabel: 'Ver',
      action,
      ttl: 9000,
    });
  }

  function prependNotificationIfVisible(n) {
    if (activePageId() !== 'notificaciones') return;
    if (typeof prependNotificationCard === 'function') prependNotificationCard(n);
  }

  async function softRefreshVentasIfNeeded(incoming) {
    if (!incoming.some(n => notifKind(n) === 'solicitud')) return;
    if (typeof refreshVentasBadge === 'function') refreshVentasBadge();
    if (activePageId() !== 'ventas' || isUserEditing()) return;
    const tab = document.querySelector('.ventas-tab-btn.active')?.dataset?.tab;
    if (tab === 'solicitudes' && typeof loadSolicitudes === 'function') {
      await loadSolicitudes();
    }
  }

  async function softRefreshMisPedidosIfNeeded(incoming) {
    if (!incoming.some(n => notifKind(n) === 'solicitud')) return;
    if (activePageId() !== 'mis-pedidos' || isUserEditing()) return;
    if (typeof loadMisPedidosPage === 'function') await loadMisPedidosPage();
  }

  async function pulseInbox() {
    if (!window._authUser || busyInbox || document.hidden) {
      setLiveIndicator(false);
      return;
    }
    setLiveIndicator(true);
    busyInbox = true;
    try {
      const after = inboxSeeded ? lastNotificationId : 0;
      const r = await fetch(`${apiBase()}/auth/notifications/pulse?after=${after}`, { credentials: 'same-origin' });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) return;

      const latest = Number(data.latest_id) || lastNotificationId;
      updateBadges(Number(data.unread) || 0);

      if (!inboxSeeded) {
        lastNotificationId = latest;
        inboxSeeded = true;
        return;
      }

      const incoming = data.new || [];
      if (incoming.length) {
        playNotifSound();
        popBadges();
        incoming.forEach(n => {
          toastForNotification(n);
          prependNotificationIfVisible(n);
        });
        lastNotificationId = Math.max(lastNotificationId, ...incoming.map(n => Number(n.notification_id) || 0), latest);
        await softRefreshVentasIfNeeded(incoming);
        await softRefreshMisPedidosIfNeeded(incoming);
      } else if (latest > lastNotificationId) {
        lastNotificationId = latest;
      }

      if (activePageId() === 'soporte' && typeof pollSoporteMessages === 'function') {
        await pollSoporteMessages();
      }
    } catch (e) {
      console.debug('[ops-live]', e);
    } finally {
      busyInbox = false;
    }
  }

  async function syncAccess() {
    if (busyAccess || document.hidden || typeof fetchMe !== 'function') return;
    busyAccess = true;
    try {
      const data = await fetchMe();
      if (!data) return;
      const user = data.user || null;
      const access = data.access;
      const sig = accessSignature(user, access);
      if (sig === lastAccessSig) return;

      const prevRole = window._authUser?.role;
      const hadUser = !!window._authUser;
      lastAccessSig = sig;
      if (typeof refreshAuthUi === 'function') refreshAuthUi(user, access);

      if (typeof notify === 'function') {
        if (hadUser && !user) notify('Tu sesión terminó.', 'warn');
        else if (user && prevRole && user.role !== prevRole) {
          notify(`Tu rol cambió a «${user.role}».`, 'info', { ttl: 5000 });
        }
      }

      const pageId = activePageId();
      if (pageId && typeof canAccessPage === 'function' && !canAccessPage(pageId)) {
        const fb = typeof defaultPageForUser === 'function' ? defaultPageForUser() : 'tienda';
        if (typeof showPage === 'function') {
          showPage(fb, document.querySelector('.nav-item[data-page="' + fb + '"]'));
        }
      }
    } catch (e) {
      console.debug('[ops-live access]', e);
    } finally {
      busyAccess = false;
    }
  }

  async function checkAndSyncStaleAnalytics() {
    if (!window._authUser || busyStale || document.hidden) return;
    if (typeof hasPermission !== 'function' || !hasPermission('elt.run')) return;
    if (typeof syncStaleAnalytics !== 'function') return;
    if (Date.now() - lastStaleSyncAt < STALE_SYNC_COOLDOWN_MS) return;

    busyStale = true;
    try {
      const r = await fetch(`${apiBase()}/meta/data-layers`, { credentials: 'same-origin' });
      if (!r.ok) return;
      const meta = await r.json().catch(() => ({}));
      if (!meta.strategic_lagging) return;

      lastStaleSyncAt = Date.now();
      await syncStaleAnalytics({ silent: true });
      if (activePageId() === 'dashboard' && typeof loadDashboard === 'function') {
        await loadDashboard();
      }
    } catch (e) {
      console.debug('[ops-live stale]', e);
    } finally {
      busyStale = false;
    }
  }

  function start() {
    stop();
    inboxTimer = setInterval(pulseInbox, INBOX_POLL_MS);
    accessTimer = setInterval(syncAccess, ACCESS_POLL_MS);
    staleTimer = setInterval(checkAndSyncStaleAnalytics, STALE_CHECK_MS);
    pulseInbox();
    checkAndSyncStaleAnalytics();
  }

  function stop() {
    if (inboxTimer) clearInterval(inboxTimer);
    if (accessTimer) clearInterval(accessTimer);
    if (staleTimer) clearInterval(staleTimer);
    inboxTimer = null;
    accessTimer = null;
    staleTimer = null;
    setLiveIndicator(false);
  }

  window.opsLiveSeed = function opsLiveSeed(user, access) {
    lastAccessSig = accessSignature(user, access);
    inboxSeeded = false;
    lastNotificationId = 0;
    setLiveIndicator(!!user);
    if (user) pulseInbox();
    else stop();
  };

  window.opsLiveRefresh = function opsLiveRefresh() {
    pulseInbox();
    syncAccess();
  };
  window.opsLivePause = stop;
  window.opsLiveResume = start;
  window.opsUxSetNotifSound = opsUxSetNotifSound;
  window.opsUxSoundEnabled = opsUxSoundEnabled;
  window.opsUxDefaultSoundForRole = opsUxDefaultSoundForRole;

  function init() {
    start();
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) pulseInbox();
      else setLiveIndicator(false);
    });
    window.addEventListener('focus', pulseInbox);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
