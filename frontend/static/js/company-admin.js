/** Perfil comercial de la empresa (logo y datos en facturas). */
(function () {
  const API = window.API || ((window.location.origin || '') + '/api');

  function el(id) {
    return document.getElementById(id);
  }

  function field(id, key, profile) {
    const node = el(id);
    if (node) node.value = profile[key] || '';
  }

  function readForm() {
    const keys = [
      'name', 'legal_name', 'tagline', 'address', 'city', 'country',
      'email', 'phone', 'tax_id', 'website', 'invoice_signer', 'invoice_footer',
    ];
    const body = {};
    keys.forEach((key) => {
      const node = el('company-field-' + key);
      if (node) body[key] = node.value.trim();
    });
    return body;
  }

  function setPreview(url) {
    const img = el('company-logo-preview');
    if (!img) return;
    if (url) {
      img.src = url + (url.includes('?') ? '&' : '?') + 't=' + Date.now();
      img.hidden = false;
    } else {
      img.hidden = true;
      img.removeAttribute('src');
    }
  }

  async function loadCompanyAdmin() {
    const panel = el('company-admin-panel');
    if (!panel || panel.hidden) return;
    const status = el('company-admin-status');
    try {
      const r = await fetch(API + '/empresa/perfil', { credentials: 'include' });
      if (!r.ok) throw new Error('No se pudo cargar el perfil');
      const data = await r.json();
      const profile = data.profile || {};
      field('company-field-name', 'name', profile);
      field('company-field-legal_name', 'legal_name', profile);
      field('company-field-tagline', 'tagline', profile);
      field('company-field-address', 'address', profile);
      field('company-field-city', 'city', profile);
      field('company-field-country', 'country', profile);
      field('company-field-email', 'email', profile);
      field('company-field-phone', 'phone', profile);
      field('company-field-tax_id', 'tax_id', profile);
      field('company-field-website', 'website', profile);
      field('company-field-invoice_signer', 'invoice_signer', profile);
      field('company-field-invoice_footer', 'invoice_footer', profile);
      setPreview(profile.logo_url);
      if (status) status.textContent = '';
    } catch (e) {
      if (status) status.textContent = e.message || 'Error al cargar';
    }
  }

  async function saveCompanyProfile() {
    const status = el('company-admin-status');
    if (status) status.textContent = 'Guardando…';
    try {
      const r = await fetch(API + '/empresa/perfil', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(readForm()),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.message || 'No se pudo guardar');
      if (status) status.textContent = 'Datos guardados correctamente.';
      if (typeof opsToast === 'function') opsToast('Perfil de empresa actualizado', 'ok');
    } catch (e) {
      if (status) status.textContent = e.message || 'Error al guardar';
      if (typeof opsToast === 'function') opsToast(e.message || 'Error al procesar', 'error');
    }
  }

  async function uploadCompanyLogo(input) {
    const file = input?.files?.[0];
    if (!file) return;
    const status = el('company-admin-status');
    if (status) status.textContent = 'Subiendo logo…';
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(API + '/empresa/perfil/logo', {
        method: 'POST',
        credentials: 'include',
        body: fd,
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.message || 'No se pudo subir el logo');
      setPreview(data.logo_url || data.profile?.logo_url);
      if (status) status.textContent = 'Logo actualizado.';
      if (typeof opsToast === 'function') opsToast('Logo actualizado', 'ok');
    } catch (e) {
      if (status) status.textContent = e.message || 'Error al subir';
      if (typeof opsToast === 'function') opsToast(e.message || 'Error al procesar', 'error');
    } finally {
      input.value = '';
    }
  }

  window.loadCompanyAdmin = loadCompanyAdmin;
  window.saveCompanyProfile = saveCompanyProfile;
  window.uploadCompanyLogo = uploadCompanyLogo;
})();
