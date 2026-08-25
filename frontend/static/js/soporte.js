/* Chat de soporte + bandeja de hilos para staff */
let soporteThread = null;
let soporteLastMessageId = 0;

function soporteEscape(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function soporteMeEmail() {
  return String(window._authUser?.email || '').trim().toLowerCase();
}

function soporteIsMine(m) {
  return String(m?.author_email || '').trim().toLowerCase() === soporteMeEmail();
}

function soporteBubbleSide(m) {
  if (isSoporteStaff()) return m.staff ? 'mine' : 'theirs';
  return soporteIsMine(m) ? 'mine' : 'theirs';
}

function soporteBubbleHtml(m) {
  const text = soporteEscape(m.text);
  const name = soporteEscape(m.author_name || m.author_email);
  const mine = soporteIsMine(m);
  const role = m.staff ? 'staff' : 'user';
  const side = soporteBubbleSide(m);
  const stamp = String(m.created_at || '').slice(0, 16).replace('T', ' ');
  return `
      <div class="chat-bubble chat-bubble--${role} chat-bubble--${side}">
        <div class="chat-meta">${name}${m.staff ? ' · Soporte' : ''}${mine ? ' · Tú' : ''}</div>
        <div class="chat-body">${text}</div>
        <div class="chat-time">${soporteEscape(stamp)}</div>
      </div>`;
}

function soporteWordCount(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean).length;
}

function updateSoporteWordHint() {
  const input = document.getElementById('soporte-input');
  const hint = document.getElementById('soporte-word-hint');
  if (!input || !hint) return;
  const n = soporteWordCount(input.value);
  hint.textContent = `${n}/100 palabras`;
  hint.classList.toggle('chat-word-hint--warn', n > 100);
}

function setSoporteComposeEnabled(enabled) {
  const input = document.getElementById('soporte-input');
  const sendBtn = document.getElementById('soporte-send-btn');
  if (input) input.disabled = !enabled;
  if (sendBtn) sendBtn.disabled = !enabled;
}

function setSoporteChatHead(title, sub) {
  const titleEl = document.getElementById('soporte-chat-title');
  const subEl = document.getElementById('soporte-chat-sub');
  if (titleEl) titleEl.textContent = title || 'Conversación';
  if (subEl) subEl.textContent = sub || '';
}

function soporteActiveThreadEmail() {
  if (isSoporteStaff()) {
    return (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase();
  }
  return soporteMeEmail();
}

function setSoporteLastMessageIdFromList(msgs) {
  if (!msgs?.length) {
    soporteLastMessageId = 0;
    return;
  }
  soporteLastMessageId = Math.max(...msgs.map(m => Number(m.message_id) || 0));
}

function appendSoporteMessages(msgs, opts) {
  const o = opts || {};
  const box = document.getElementById('soporte-messages');
  if (!box || !msgs?.length) return;
  const wasEmpty = !!box.querySelector('.ops-empty, .catalog-empty');
  if (wasEmpty) {
    box.innerHTML = msgs.map(soporteBubbleHtml).join('');
  } else {
    box.insertAdjacentHTML('beforeend', msgs.map(soporteBubbleHtml).join(''));
  }
  box.scrollTop = box.scrollHeight;
  soporteLastMessageId = Math.max(soporteLastMessageId, ...msgs.map(m => Number(m.message_id) || 0));

  if (o.toast && typeof opsToast === 'function') {
    const last = msgs[msgs.length - 1];
    const who = last.staff ? 'Soporte' : (last.author_name || 'Cliente');
    opsToast(`${who}: ${String(last.text || '').slice(0, 140)}`, last.staff ? 'info' : 'ok', { ttl: 7000 });
  }
}

async function pollSoporteMessages() {
  if (!window._authUser) return;
  const thread = soporteActiveThreadEmail();
  if (!thread) return;

  const q = new URLSearchParams({ thread, after: String(soporteLastMessageId || 0) });
  const r = await fetch(`${API}/soporte/mensajes?${q}`, { credentials: 'same-origin' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) return;

  const msgs = data.messages || [];
  if (msgs.length) {
    const typing = document.activeElement?.id === 'soporte-input';
    appendSoporteMessages(msgs, { toast: !typing });
    if (isSoporteStaff() && typeof loadSoporteInbox === 'function') {
      await loadSoporteInbox();
    }
  } else if (data.latest_id && data.latest_id > soporteLastMessageId) {
    soporteLastMessageId = Number(data.latest_id);
  }
}

window.pollSoporteMessages = pollSoporteMessages;

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

function applySoporteRoleUi() {
  const isStaff = isSoporteStaff();
  const page = document.getElementById('page-soporte');
  const lead = document.getElementById('soporte-lead');
  const adminBar = document.getElementById('soporte-admin-bar');
  const inbox = document.getElementById('soporte-inbox');
  if (page) {
    page.classList.toggle('soporte-page--staff', isStaff);
    page.classList.toggle('soporte-page--user', !isStaff);
  }
  if (lead) {
    lead.textContent = isStaff
      ? 'Responde los hilos de clientes desde la bandeja. Tus mensajes salen como soporte.'
      : 'Escribe al equipo comercial. Te responden en este mismo hilo.';
  }
  if (adminBar) adminBar.hidden = !isStaff;
  if (inbox) inbox.hidden = !isStaff;
}

async function loadSoportePage() {
  const box = document.getElementById('soporte-messages');
  if (!box) return;
  if (!window._authUser) {
    applySoporteRoleUi();
    setSoporteComposeEnabled(false);
    setSoporteChatHead('Soporte', 'Inicia sesión para escribir');
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Inicia sesión', hint: 'Accede para contactar al equipo de soporte.' })
      : '<p class="catalog-empty">Inicia sesión para contactar soporte.</p>';
    const inbox = document.getElementById('soporte-inbox');
    if (inbox) inbox.hidden = true;
    const chips = document.getElementById('soporte-chips');
    if (chips) chips.innerHTML = '';
    return;
  }

  const isStaff = isSoporteStaff();
  applySoporteRoleUi();
  if (isStaff) await loadSoporteInbox();
  else renderSoporteChips([]);

  const thread = isStaff
    ? (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase()
    : soporteMeEmail();
  if (isStaff && !thread) {
    setSoporteComposeEnabled(false);
    setSoporteChatHead('Bandeja de soporte', 'Elige un hilo a la izquierda');
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Elige un hilo', hint: 'Selecciona una conversación de la bandeja o indica el correo del cliente.' })
      : '<p class="catalog-empty">Elige un hilo de la bandeja o indica un correo de cliente.</p>';
    return;
  }

  soporteThread = thread;
  setSoporteComposeEnabled(true);
  setSoporteChatHead(
    isStaff ? thread : 'Tu conversación',
    isStaff ? 'Responde como equipo de soporte' : 'Tus mensajes a la derecha · el equipo responde a la izquierda'
  );

  const q = thread ? `?thread=${encodeURIComponent(thread)}` : '';
  const r = await fetch(API + '/soporte/mensajes' + q, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    box.innerHTML = `<p class="catalog-empty">${soporteEscape(data.message || 'Error al procesar')}</p>`;
    return;
  }
  const msgs = data.messages || [];
  if (!msgs.length) {
    box.innerHTML = typeof opsEmpty === 'function'
      ? opsEmpty({ title: 'Sin mensajes aún', hint: 'Escribe abajo para iniciar la conversación.' })
      : '<p class="catalog-empty">Sin mensajes aún. Escribe abajo para iniciar la conversación.</p>';
    soporteLastMessageId = Number(data.latest_id) || 0;
  } else {
    box.innerHTML = msgs.map(soporteBubbleHtml).join('');
    box.scrollTop = box.scrollHeight;
  }
  setSoporteLastMessageIdFromList(msgs);
}

async function loadSoporteInbox() {
  const list = document.getElementById('soporte-inbox-list');
  if (!list) return;
  list.innerHTML = '<p class="catalog-empty" style="padding:8px">Cargando hilos…</p>';
  const r = await fetch(API + '/soporte/hilos?limit=40', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    list.innerHTML = `<p class="catalog-empty">${soporteEscape(data.message || 'Error al procesar')}</p>`;
    return;
  }
  const threads = data.threads || [];
  renderSoporteChips(threads);
  if (!threads.length) {
    list.innerHTML = '<p class="catalog-empty" style="padding:8px">Sin conversaciones aún.</p>';
    return;
  }
  list.innerHTML = threads.map(t => {
    const email = String(t.thread_email || '');
    const pending = t.awaiting_staff;
    return `
    <button type="button" class="soporte-thread-btn ${soporteThread === email ? 'active' : ''}" data-thread="${soporteEscape(email)}">
      <strong>${soporteEscape(email)}</strong>
      <span class="soporte-thread-preview">${soporteEscape((t.last_message || '').slice(0, 80))}</span>
      <span class="soporte-thread-meta">${pending ? '● Pendiente' : 'Respondido'} · ${soporteEscape(String(t.last_at || '').slice(0, 16).replace('T', ' '))}</span>
    </button>`;
  }).join('');
  list.querySelectorAll('[data-thread]').forEach(btn => {
    btn.addEventListener('click', () => openSoporteThread(btn.getAttribute('data-thread')));
  });
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
  if (soporteWordCount(text) > 100) {
    notifyWarn('El mensaje no puede superar 100 palabras.');
    return;
  }
  const isStaff = isSoporteStaff();
  const body = { text };
  if (isStaff) {
    body.as_staff = true;
    body.thread_email = (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase();
    if (!body.thread_email) {
      notifyWarn('Indica el correo del cliente.');
      return;
    }
    if (body.thread_email === soporteMeEmail()) {
      body.as_staff = false;
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
    notifyErr(data.message || 'Error al procesar');
    return;
  }
  if (input) input.value = '';
  updateSoporteWordHint();
  notifyOk('Mensaje enviado.');
  loadSoportePage();
  if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
}

window.openSoporteThread = openSoporteThread;
window.sendSoporteMessage = sendSoporteMessage;

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('soporte-input');
  const sendBtn = document.getElementById('soporte-send-btn');
  if (input) {
    input.addEventListener('input', updateSoporteWordHint);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendSoporteMessage();
      }
    });
    updateSoporteWordHint();
  }
  if (sendBtn) sendBtn.addEventListener('click', sendSoporteMessage);
});
