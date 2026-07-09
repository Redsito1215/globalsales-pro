/* Administración de roles y usuarios */
let rolesAdminState = { roles: [], users: [], editingSlug: null };

async function loadRolesAdminPage() {
  if (window._authUser?.role !== 'administrador') {
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
  if (!body) return;
  body.innerHTML = '<tr><td colspan="4">Cargando…</td></tr>';
  const r = await fetch(API + '/auth/roles', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="4">${data.message || 'Error'}</td></tr>`;
    return;
  }
  rolesAdminState.roles = data.roles || [];
  body.innerHTML = rolesAdminState.roles.map(role => `
    <tr>
      <td><code>${role.slug}</code>${role.system ? ' <span class="badge">sistema</span>' : ''}</td>
      <td>${role.label}</td>
      <td>${(role.pages || []).length} páginas</td>
      <td>
        <button type="button" class="btn btn-ghost" style="font-size:11px;padding:4px 8px" onclick="openRoleEditor('${role.slug}')">Editar</button>
        ${role.system ? '' : `<button type="button" class="btn btn-ghost" style="font-size:11px;padding:4px 8px" onclick="deleteRole('${role.slug}')">Eliminar</button>`}
      </td>
    </tr>`).join('');
}

async function loadUsersList() {
  const body = document.getElementById('roles-admin-users-body');
  if (!body) return;
  const r = await fetch(API + '/auth/users', { credentials: 'same-origin' });
  const data = await r.json();
  if (!r.ok) {
    body.innerHTML = `<tr><td colspan="4">${data.message || 'Error'}</td></tr>`;
    return;
  }
  rolesAdminState.users = data.users || [];
  const assignable = data.assignable_roles || [];
  body.innerHTML = rolesAdminState.users.map(u => {
    const opts = assignable.map(r =>
      `<option value="${r.slug}" ${r.slug === u.role ? 'selected' : ''}>${r.label}</option>`
    ).join('');
    return `<tr>
      <td>${u.name}<br><span style="font-size:10px;color:var(--muted)">${u.email}</span></td>
      <td><select onchange="changeUserRole('${u.id}', this.value)" style="font-size:12px;padding:4px 8px">${opts}</select></td>
      <td>${u.role}</td>
      <td>—</td>
    </tr>`;
  }).join('');
}

function openRoleEditor(slug) {
  const role = rolesAdminState.roles.find(r => r.slug === slug);
  if (!role) return;
  rolesAdminState.editingSlug = slug;
  document.getElementById('role-editor-title').textContent = slug ? `Editar rol: ${role.label}` : 'Nuevo rol';
  document.getElementById('role-editor-slug').value = slug || '';
  document.getElementById('role-editor-slug').disabled = !!slug;
  document.getElementById('role-editor-label').value = role.label || '';
  document.getElementById('role-editor-assignable').checked = role.assignable !== false;
  const catalog = window._access?.page_catalog || {};
  const permCat = window._access?.permission_catalog || {};
  document.getElementById('role-editor-pages').innerHTML = Object.entries(catalog).map(([id, meta]) =>
    `<label style="display:block;font-size:12px;margin:4px 0">
      <input type="checkbox" name="role-page" value="${id}" ${(role.pages || []).includes(id) ? 'checked' : ''} />
      ${meta.label || id}
    </label>`
  ).join('');
  document.getElementById('role-editor-perms').innerHTML = Object.entries(permCat).map(([id, label]) =>
    `<label style="display:block;font-size:12px;margin:4px 0">
      <input type="checkbox" name="role-perm" value="${id}" ${(role.permissions || []).includes(id) ? 'checked' : ''} />
      ${label}
    </label>`
  ).join('');
  document.getElementById('role-editor-modal').hidden = false;
}

function openRoleCreate() {
  rolesAdminState.editingSlug = null;
  document.getElementById('role-editor-title').textContent = 'Nuevo rol';
  document.getElementById('role-editor-slug').value = '';
  document.getElementById('role-editor-slug').disabled = false;
  document.getElementById('role-editor-label').value = '';
  document.getElementById('role-editor-assignable').checked = true;
  const catalog = window._access?.page_catalog || {};
  const permCat = window._access?.permission_catalog || {};
  document.getElementById('role-editor-pages').innerHTML = Object.entries(catalog).map(([id, meta]) =>
    `<label style="display:block;font-size:12px;margin:4px 0">
      <input type="checkbox" name="role-page" value="${id}" ${id === 'tienda' ? 'checked' : ''} />
      ${meta.label || id}
    </label>`
  ).join('');
  document.getElementById('role-editor-perms').innerHTML = Object.entries(permCat).map(([id, label]) =>
    `<label style="display:block;font-size:12px;margin:4px 0">
      <input type="checkbox" name="role-perm" value="${id}" ${id === 'shop.view' ? 'checked' : ''} />
      ${label}
    </label>`
  ).join('');
  document.getElementById('role-editor-modal').hidden = false;
}

function closeRoleEditor() {
  document.getElementById('role-editor-modal').hidden = true;
}

async function saveRoleEditor() {
  const slug = document.getElementById('role-editor-slug').value.trim();
  const label = document.getElementById('role-editor-label').value.trim();
  const pages = [...document.querySelectorAll('#role-editor-pages input:checked')].map(cb => cb.value);
  const permissions = [...document.querySelectorAll('#role-editor-perms input:checked')].map(cb => cb.value);
  const assignable = document.getElementById('role-editor-assignable').checked;
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
  if (!r.ok) { alert(data.message || 'Error'); return; }
  closeRoleEditor();
  await loadRolesAdminPage();
  const me = await fetch(API + '/auth/me', { credentials: 'same-origin' }).then(r => r.json()).catch(() => null);
  if (me?.user) refreshAuthUi(me.user, me.access);
}

async function deleteRole(slug) {
  if (!confirm('¿Eliminar rol ' + slug + '?')) return;
  const r = await fetch(`${API}/auth/roles/${encodeURIComponent(slug)}`, {
    method: 'DELETE', credentials: 'same-origin',
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); return; }
  await loadRolesList();
}

async function changeUserRole(userId, role) {
  const r = await fetch(`${API}/auth/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ role }),
  });
  const data = await r.json();
  if (!r.ok) { alert(data.message || 'Error'); await loadUsersList(); return; }
  await loadUsersList();
}
