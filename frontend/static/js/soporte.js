/* Chat de soporte + bandeja de hilos para staff */
let soporteThread = null;

function isSoporteStaff() {
  return hasPermission('soporte.inbox') || window._authUser?.role === 'administrador';
}

function renderSoporteChips(threads) {
  const chips = document.getElementById('soporte-chips');
  if (!chips) return;
  if (!isSoporteStaff()) {
    chips.innerHTML = '<span class="ops-chip ops-chip--muted"><span>Tu conversación</span><strong>1</strong></span>';
    return;
  }
  const list = threads || [];
  const pending = list.filter(t => t.awaiting_staff).length;
  chips.innerHTML = `
    <span class="ops-chip"><span>Hilos</span><strong>${list.length}</strong></span>
    <span class="ops-chip ${pending ? 'ops-chip--warn' : 'ops-chip--muted'}"><span>Pendientes</span><strong>${pending}</strong></span>`;
}

async function loadSoportePage() {
  const box = document.getElementById('soporte-messages');
  const adminBar = document.getElementById('soporte-admin-bar');
  const inbox = document.getElementById('soporte-inbox');
  if (!box) return;
  if (!window._authUser) {
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Inicia sesión', hint: 'Accede para contactar al equipo de soporte.' })
      : '<p class="catalog-empty">Inicia sesión para contactar soporte.</p>';
    if (inbox) inbox.hidden = true;
    const chips = document.getElementById('soporte-chips');
    if (chips) chips.innerHTML = '';
    return;
  }
  const isStaff = isSoporteStaff();
  if (adminBar) adminBar.hidden = !isStaff;
  if (inbox) inbox.hidden = !isStaff;
  if (isStaff) await loadSoporteInbox();
  else renderSoporteChips([]);

  const thread = isStaff
    ? (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase()
    : (window._authUser.email || '').toLowerCase();
  if (isStaff && !thread) {
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Elige un hilo', hint: 'Selecciona una conversación de la bandeja o indica el correo del cliente.' })
      : '<p class="catalog-empty">Elige un hilo de la bandeja o indica un correo de cliente.</p>';
    return;
  }
  soporteThread = thread;
  const q = thread ? `?thread=${encodeURIComponent(thread)}` : '';
  const r = await fetch(API + '/soporte/mensajes' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    box.innerHTML = `<p class="catalog-empty">${data.message || 'Error'}</p>`;
    return;
  }
  const msgs = data.messages || [];
  if (!msgs.length) {
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Sin mensajes aún', hint: 'Escribe abajo para iniciar la conversación.' })
      : '<p class="catalog-empty">Sin mensajes aún. Escribe abajo para iniciar la conversación.</p>';
  } else {
    box.innerHTML = msgs.map(m => `
      <div class="chat-bubble ${m.staff ? 'chat-bubble--staff' : 'chat-bubble--user'}">
        <div class="chat-meta">${m.author_name || m.author_email}${m.staff ? ' · Soporte' : ''}</div>
        <div>${m.text.replace(/</g, '&lt;')}</div>
        <div class="chat-time">${(m.created_at || '').slice(0, 16).replace('T', ' ')}</div>
      </div>`).join('');
    box.scrollTop = box.scrollHeight;
  }
}

async function loadSoporteInbox() {
  const list = document.getElementById('soporte-inbox-list');
  if (!list) return;
  list.innerHTML = '<p class="catalog-empty" style="padding:8px">Cargando hilos…</p>';
  const r = await fetch(API + '/soporte/hilos?limit=40', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    list.innerHTML = `<p class="catalog-empty">${data.message || 'Error'}</p>`;
    return;
  }
  const threads = data.threads || [];
  renderSoporteChips(threads);
  if (!threads.length) {
    list.innerHTML = '<p class="catalog-empty" style="padding:8px">Sin conversaciones aún.</p>';
    return;
  }
  list.innerHTML = threads.map(t => `
    <button type="button" class="soporte-thread-btn ${soporteThread === t.thread_email ? 'active' : ''}"
      onclick="openSoporteThread('${String(t.thread_email).replace(/'/g, "\\'")}')">
      <strong>${t.thread_email}</strong>
      <span class="soporte-thread-preview">${(t.last_message || '').slice(0, 80)}</span>
      <span class="soporte-thread-meta">${t.awaiting_staff ? '● Pendiente' : 'Respondido'} · ${(t.last_at || '').slice(0, 16).replace('T', ' ')}</span>
    </button>`).join('');
}

function openSoporteThread(email) {
  const input = document.getElementById('soporte-thread-email');
  if (input) input.value = email;
  soporteThread = email;
  loadSoportePage();
}

async function sendSoporteMessage() {
  const input = document.getElementById('soporte-input');
  const text = (input?.value || '').trim();
  if (!text) return;
  const isStaff = isSoporteStaff();
  const body = { text };
  if (isStaff) {
    body.as_staff = true;
    body.thread_email = (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase();
    if (!body.thread_email) {
      if (typeof opsToast === 'function') opsToast('Indica el correo del cliente.', 'warn');
      else alert('Indica el correo del cliente.');
      return;
    }
  }
  const r = await fetch(API + '/soporte/mensajes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) {
    if (typeof opsToast === 'function') opsToast(data.message || 'Error', 'danger');
    else alert(data.message || 'Error');
    return;
  }
  if (input) input.value = '';
  loadSoportePage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

window.openSoporteThread = openSoporteThread;
