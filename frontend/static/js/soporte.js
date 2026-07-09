/* Chat de soporte */
let soporteThread = null;

async function loadSoportePage() {
  const box = document.getElementById('soporte-messages');
  const adminBar = document.getElementById('soporte-admin-bar');
  if (!box) return;
  if (!window._authUser) {
    box.innerHTML = '<p class="catalog-empty">Inicia sesión para contactar soporte.</p>';
    return;
  }
  const isStaff = ['administrador', 'vendedor'].includes(window._authUser.role);
  if (adminBar) adminBar.hidden = !isStaff;
  const thread = isStaff
    ? (document.getElementById('soporte-thread-email')?.value || '').trim().toLowerCase()
    : (window._authUser.email || '').toLowerCase();
  if (isStaff && !thread) {
    box.innerHTML = '<p class="catalog-empty">Indica el correo del cliente para ver o responder su hilo.</p>';
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
    box.innerHTML = '<p class="catalog-empty">Sin mensajes aún. Escribe abajo para iniciar la conversación.</p>';
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

async function sendSoporteMessage() {
  const input = document.getElementById('soporte-input');
  const text = (input?.value || '').trim();
  if (!text) return;
  const isStaff = ['administrador', 'vendedor'].includes(window._authUser?.role);
  const body = { text };
  if (isStaff) {
    body.as_staff = true;
    body.thread_email = (document.getElementById('soporte-thread-email')?.value || soporteThread || '').trim().toLowerCase();
    if (!body.thread_email) { alert('Indica el correo del cliente.'); return; }
  }
  const r = await fetch(API + '/soporte/mensajes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  if (input) input.value = '';
  loadSoportePage();
}
