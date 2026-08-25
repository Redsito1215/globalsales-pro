/* Administración de roles y usuarios */
const ADMIN_ROLE_SLUG = 'administrador';
const FALLBACK_USER_ROLE = 'cliente';

let rolesAdminState = { roles: [], users: [], editingSlug: null, userQuery: '' };
let usersSearchTimer = null;

function canManageUsers() {
  return typeof hasPermission === 'function' && hasPermission('users.manage');
}

function roleLabelBySlug(slug) {
  const role = rolesAdminState.roles.find(r => r.slug === slug);
  return role?.label || slug;
}

function roleActionsCell(role) {
  const slug = role.slug;
  const inactive = role.active === false;
  if (slug === ADMIN_ROLE_SLUG) {
    return '<span class="admin-role-note">Acceso total</span>';
  }
  if (inactive) {
    return `<div class="table-actions">
      <button type="button" class="btn btn-primary btn-ops btn-sm" onclick="enableRole('${slug}')">Habilitar</button>
    </div>`;
  }
  const editBtn = `<button type="button" class="btn btn-ghost btn-ops btn-sm" onclick="openRoleEditor('${slug}')">Editar</button>`;
  if (slug === FALLBACK_USER_ROLE) {
    return `<div class="table-actions">${editBtn}</div>`;
  }
  return `<div class="table-actions">${editBtn}
    <button type="button" class="btn btn-ghost btn-ops btn-sm" onclick="disableRole('${slug}')">Inhabilitar</button>
  </div>`;
}

function renderRoleChecklist(containerId, entries, name, selected, defaults) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = Object.entries(entries).map(([id, meta]) => {
    const label = typeof meta === 'string' ? meta : (meta.label || id);
    const checked = (selected || []).includes(id) || (defaults || []).includes(id);
    return `<label><input type="checkbox" name="${name}" value="${id}" ${checked ? 'checked' : ''} /> ${label}</label>`;
  }).join('');
}

async function loadRolesAdminPage() {
  if (!canManageUsers()) {
    document.getElementById('roles-admin-denied').hidden = false;
    document.getElementById('roles-admin-content').hidden = true;
    return;
  }
  document.getElementById('roles-admin-denied').hidden = true;
  document.getElementById('roles-admin-content').hidden = false;
  await Promise.all([loadRolesList(), loadUsersList()]);
}

async function loadRolesList() {
  const body = document.getElementById('roles-admin-roles-body');
  const meta = document.getElementById('roles-admin-meta');
  if (!body) return;
  body.innerHTML = typeof opsEmptyRow === 'function'
    ? opsEmptyRow(4, { title: 'Cargando roles…', hint: 'Un momento.' })
    : '<tr><td colspan="4">Cargando…</td></tr>';
  const r = await fetch(API + '/auth/roles', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="4">${data.message || 'Error al procesar'}</td></tr>`;
    if (meta) meta.textContent = '';
    return;
  }
  rolesAdminState.roles = data.roles || [];
  const activeCount = rolesAdminState.roles.filter(r => r.active !== false).length;
  if (meta) meta.textContent = `${rolesAdminState.roles.length} roles · ${activeCount} activos`;
  if (!rolesAdminState.roles.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(4, { title: 'Sin roles', hint: 'Crea un rol con el botón superior.' })
      : '<tr><td colspan="4">Sin roles</td></tr>';
    return;
  }
  body.innerHTML = rolesAdminState.roles.map(role => {
    const slug = role.slug;
    const inactive = role.active === false;
    const statusBadge = inactive ? ' <span class="badge badge--muted">Inactivo</span>' : '';
    const systemBadge = role.system ? ' <span class="badge badge--system">Sistema</span>' : '';
    const pagesText = slug === ADMIN_ROLE_SLUG ? 'Todas las páginas' : `${(role.pages || []).length} páginas`;
    return `
    <tr>
      <td><code>${slug}</code>${systemBadge}${statusBadge}</td>
      <td>${role.label}</td>
      <td>${pagesText}</td>
      <td>${roleActionsCell(role)}</td>
    </tr>`;
  }).join('');
}

function userRoleCell(u, assignable) {
  const selfId = window._authUser?.id;
  const isSelf = selfId && u.id === selfId;
  const isAdmin = u.role === ADMIN_ROLE_SLUG;
  if (isAdmin) {
    return `<span class="badge badge--system">${roleLabelBySlug(u.role)}</span>`;
  }
  if (isSelf) {
    return `<span class="badge badge--muted">${roleLabelBySlug(u.role)} · tú</span>`;
  }
  const opts = assignable.map(r =>
    `<option value="${r.slug}" ${r.slug === u.role ? 'selected' : ''}>${r.label}</option>`
  ).join('');
  return `<select class="role-user-select" aria-label="Rol de ${u.email}" onchange="changeUserRole('${u.id}', this.value)">${opts}</select>`;
}

function userActionsCell(u) {
  const selfId = window._authUser?.id;
  const isSelf = selfId && u.id === selfId;
  const isAdmin = u.role === ADMIN_ROLE_SLUG;
  if (isSelf || isAdmin) {
    return '<span class="admin-role-note">—</span>';
  }
  return `<button type="button" class="btn btn-ghost btn-ops btn-sm" onclick="deactivateUser('${u.id}')">Desactivar</button>`;
}

async function loadUsersList() {
  const body = document.getElementById('roles-admin-users-body');
  const meta = document.getElementById('roles-users-meta');
  if (!body) return;
  body.innerHTML = typeof opsEmptyRow === 'function'
    ? opsEmptyRow(4, { title: 'Cargando usuarios…', hint: 'Un momento.' })
    : '<tr><td colspan="4">Cargando…</td></tr>';
  const q = rolesAdminState.userQuery || '';
  const url = `${API}/auth/users?limit=200${q ? '&q=' + encodeURIComponent(q) : ''}`;
  const r = await fetch(url, { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="4">${data.message || 'Error al procesar'}</td></tr>`;
    if (meta) meta.textContent = '';
    return;
  }
  rolesAdminState.users = data.users || [];
  const assignable = data.assignable_roles || [];
  const total = data.total ?? rolesAdminState.users.length;
  if (meta) {
    meta.textContent = q
      ? `${rolesAdminState.users.length} de ${total} usuarios · filtro «${q}»`
      : `${total} usuarios activos`;
  }
  if (!rolesAdminState.users.length) {
    body.innerHTML = typeof opsEmptyRow === 'function'
      ? opsEmptyRow(4, { title: q ? 'Sin coincidencias' : 'Sin usuarios', hint: q ? 'Prueba otro término.' : 'Registra cuentas desde autenticación.' })
      : '<tr><td colspan="4">Sin usuarios</td></tr>';
    return;
  }
  body.innerHTML = rolesAdminState.users.map(u => {
    return `<tr>
      <td><span class="audit-cell-user">${u.name}</span><span class="role-user-email">${u.email}</span></td>
      <td><code>${u.role}</code></td>
      <td>${userRoleCell(u, assignable)}</td>
      <td>${userActionsCell(u)}</td>
    </tr>`;
  }).join('');
}

function onUsersSearchInput(value) {
  rolesAdminState.userQuery = (value || '').trim();
  if (usersSearchTimer) clearTimeout(usersSearchTimer);
  usersSearchTimer = setTimeout(() => loadUsersList(), 280);
}

function openRoleEditor(slug) {
  const role = rolesAdminState.roles.find(r => r.slug === slug);
  if (!role) return;
  if (slug === ADMIN_ROLE_SLUG) {
    notifyWarn('El rol administrador tiene acceso total y no se puede editar.');
    return;
  }
  if (role.active === false) {
    notifyWarn('Este rol está inhabilitado.');
    return;
  }
  rolesAdminState.editingSlug = slug;
  document.getElementById('role-editor-title').textContent = `Editar rol: ${role.label}`;
  document.getElementById('role-editor-slug').value = slug || '';
  document.getElementById('role-editor-slug').disabled = !!slug;
  document.getElementById('role-editor-label').value = role.label || '';
  document.getElementById('role-editor-assignable').checked = role.assignable !== false;
  renderRoleChecklist('role-editor-pages', window._access?.page_catalog || {}, 'role-page', role.pages || [], []);
  renderRoleChecklist('role-editor-perms', window._access?.permission_catalog || {}, 'role-perm', role.permissions || [], []);
  const modal = document.getElementById('role-editor-modal');
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
}

function openRoleCreate() {
  rolesAdminState.editingSlug = null;
  document.getElementById('role-editor-title').textContent = 'Nuevo rol';
  document.getElementById('role-editor-slug').value = '';
  document.getElementById('role-editor-slug').disabled = false;
  document.getElementById('role-editor-label').value = '';
  document.getElementById('role-editor-assignable').checked = true;
  renderRoleChecklist('role-editor-pages', window._access?.page_catalog || {}, 'role-page', [], ['tienda']);
  renderRoleChecklist('role-editor-perms', window._access?.permission_catalog || {}, 'role-perm', [], ['shop.view']);
  const modal = document.getElementById('role-editor-modal');
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
}

function closeRoleEditor() {
  const modal = document.getElementById('role-editor-modal');
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
}

async function saveRoleEditor() {
  const label = document.getElementById('role-editor-label').value.trim();
  const pages = [...document.querySelectorAll('#role-editor-pages input:checked')].map(cb => cb.value);
  const permissions = [...document.querySelectorAll('#role-editor-perms input:checked')].map(cb => cb.value);
  const assignable = document.getElementById('role-editor-assignable').checked;
  if (!pages.length) {
    notifyWarn('Debes dejar al menos una página marcada.');
    return;
  }
  const body = { label, pages, permissions, assignable };
  const newSlug = document.getElementById('role-editor-slug').value.trim();
  const editing = rolesAdminState.editingSlug;
  const url = editing ? `${API}/auth/roles/${encodeURIComponent(editing)}` : `${API}/auth/roles`;
  const r = await fetch(url, {
    method: editing ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(editing ? body : { ...body, slug: newSlug }),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error al procesar'); return; }
  closeRoleEditor();
  await loadRolesAdminPage();
  const me = await fetch(API + '/auth/me', { credentials: 'same-origin' }).then(res => res.json()).catch(() => null);
  if (me?.user) refreshAuthUi(me.user, me.access);
  notifyOk('Rol guardado.');
  if (typeof opsLiveRefresh === 'function') opsLiveRefresh();
}

async function disableRole(slug) {
  if (slug === ADMIN_ROLE_SLUG || slug === FALLBACK_USER_ROLE) {
    notifyWarn('Este rol no se puede inhabilitar.');
    return;
  }
  const role = rolesAdminState.roles.find(r => r.slug === slug);
  if (role?.active === false) {
    notifyWarn('Este rol ya está inhabilitado.');
    return;
  }
  const label = role?.label || slug;
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: `Inhabilitar rol «${label}»`,
    message: 'No se eliminará. Los usuarios con ese rol pasarán a cliente (usuario normal) hasta que les asignes otro rol.',
    confirmLabel: 'Inhabilitar',
    danger: true,
  });
  if (!ok) return;
  const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
  let r;
  try {
    r = await fetch(`${base}/auth/roles/${encodeURIComponent(slug)}/inhabilitar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
  } catch (e) {
    notifyErr('Error de red al inhabilitar el rol.');
    return;
  }
  let data = {};
  try {
    data = await r.json();
  } catch (_) {
    notifyErr(`No se pudo inhabilitar el rol (${r.status}).`);
    return;
  }
  if (!r.ok) {
    notifyErr(data.message || `No se pudo inhabilitar el rol (${r.status}).`);
    return;
  }
  notifyOk(data.message || 'Rol inhabilitado.');
  await loadRolesAdminPage();
  if (typeof opsLiveRefresh === 'function') opsLiveRefresh();
}

async function enableRole(slug) {
  if (slug === ADMIN_ROLE_SLUG) {
    notifyWarn('El rol administrador siempre está activo.');
    return;
  }
  const role = rolesAdminState.roles.find(r => r.slug === slug);
  if (role?.active !== false) {
    notifyWarn('Este rol ya está activo.');
    return;
  }
  const label = role?.label || slug;
  if (typeof opsConfirm !== 'function') {
    notifyErr('No se pudo abrir la confirmación. Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: `Habilitar rol «${label}»`,
    message: 'El rol volverá a estar disponible para asignar. Los usuarios que pasaron a cliente no se cambian solos; asígnales el rol manualmente si corresponde.',
    confirmLabel: 'Habilitar',
  });
  if (!ok) return;
  const base = (typeof API !== 'undefined' && API) ? API : (window.location.origin + '/api');
  let r;
  try {
    r = await fetch(`${base}/auth/roles/${encodeURIComponent(slug)}/habilitar`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
  } catch (e) {
    notifyErr('Error de red al habilitar el rol.');
    return;
  }
  let data = {};
  try {
    data = await r.json();
  } catch (_) {
    notifyErr(`No se pudo habilitar el rol (${r.status}).`);
    return;
  }
  if (!r.ok) {
    notifyErr(data.message || `No se pudo habilitar el rol (${r.status}).`);
    return;
  }
  notifyOk(data.message || 'Rol habilitado.');
  await loadRolesAdminPage();
  if (typeof opsLiveRefresh === 'function') opsLiveRefresh();
}

window.disableRole = disableRole;
window.enableRole = enableRole;
window.onUsersSearchInput = onUsersSearchInput;

async function changeUserRole(userId, role) {
  const r = await fetch(`${API}/auth/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ role }),
  });
  const data = await r.json();
  if (!r.ok) { notifyErr(data.message || 'Error al procesar'); await loadUsersList(); return; }
  notifyOk(`Rol actualizado a ${roleLabelBySlug(role)}.`);
  await loadUsersList();
  if (typeof opsLiveRefresh === 'function') opsLiveRefresh();
}

async function deactivateUser(userId) {
  const user = rolesAdminState.users.find(u => u.id === userId);
  const label = user?.email || userId;
  if (typeof opsConfirm !== 'function') {
    notifyErr('Recarga la página (Ctrl+F5).');
    return;
  }
  const ok = await opsConfirm({
    title: 'Desactivar cuenta',
    message: `La cuenta ${label} no podrá iniciar sesión. Puedes crear otra con el mismo correo más adelante si hace falta.`,
    confirmLabel: 'Desactivar',
    danger: true,
  });
  if (!ok) return;
  const r = await fetch(`${API}/auth/users/${encodeURIComponent(userId)}/inhabilitar`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  const data = await r.json();
  if (!r.ok) {
    notifyErr(data.message || 'No se pudo desactivar la cuenta.');
    return;
  }
  notifyOk(data.message || 'Cuenta desactivada.');
  await loadUsersList();
}

window.deactivateUser = deactivateUser;
