/* Q2 Análisis — exportación CSV */
async function exportAnalysis() {
  if (!window._authUser) {
    alert('Debes iniciar sesión para exportar.');
    openLoginModal();
    return;
  }
  if (!hasPermission('analysis.export')) {
    alert('Tu rol no incluye permiso para exportar CSV.');
    return;
  }
  const q = new URLSearchParams();
  const region = document.getElementById('an-region')?.value;
  const item = document.getElementById('an-itemtype')?.value;
  const channel = document.getElementById('an-channel')?.value;
  const priority = document.getElementById('an-priority')?.value;
  if (region) q.set('region', region);
  if (item) q.set('item_type', item);
  if (channel) q.set('channel', channel);
  if (priority) q.set('priority', priority);
  const r = await fetch(API + '/analysis/export?' + q, { credentials: 'same-origin' });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    alert(d.message || 'Error al exportar');
    return;
  }
  const blob = await r.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'globtrade_export.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

async function loadAnalisisExportPage() {
  const st = document.getElementById('export-status');
  if (st) st.textContent = window._authUser
    ? 'Listo para exportar con tus filtros.'
    : 'Inicia sesión como analista o administrador.';
}
