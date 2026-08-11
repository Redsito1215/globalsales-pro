/* Q2 Análisis — exportación CSV */
async function exportAnalysis() {
  if (!window._authUser) {
    notifyWarn('Debes iniciar sesión para exportar.');
    openLoginModal();
    return;
  }
  if (!hasPermission('analysis.export')) {
    notifyWarn('Tu rol no incluye permiso para exportar CSV.');
    return;
  }
  const st = document.getElementById('export-status');
  if (st) st.textContent = 'Exportando…';
  const q = new URLSearchParams();
  const region = document.getElementById('an-region')?.value;
  const item = document.getElementById('an-itemtype')?.value;
  const channel = document.getElementById('an-channel')?.value;
  const priority = document.getElementById('an-priority')?.value;
  const months = document.getElementById('an-months')?.value;
  const limit = document.getElementById('an-limit')?.value || '5000';
  if (region) q.set('region', region);
  if (item) q.set('item_type', item);
  if (channel) q.set('channel', channel);
  if (priority) q.set('priority', priority);
  if (months) q.set('months', months);
  q.set('limit', limit);
  const r = await fetch(API + '/analysis/export?' + q, { credentials: 'same-origin' });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    if (st) st.textContent = d.message || 'Error al exportar';
    notifyErr(d.message || 'Error al exportar');
    return;
  }
  const rows = r.headers.get('X-Export-Rows') || '?';
  const truncated = r.headers.get('X-Export-Truncated') === '1';
  const blob = await r.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'globtrade_export.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  const msg = truncated
    ? `CSV descargado: ${rows} filas (truncado al límite). Ajusta el límite si necesitas más.`
    : `CSV descargado: ${rows} filas.`;
  if (st) st.textContent = msg;
  if (typeof opsToast === 'function') opsToast(msg, truncated ? 'warn' : 'ok');
}

async function loadAnalisisExportPage() {
  const st = document.getElementById('export-status');
  if (st) {
    st.textContent = window._authUser
      ? 'Listo. Exporta hasta el límite elegido (máx. 50 000). El periodo se ancla al histórico del DW.'
      : 'Inicia sesión como analista o administrador.';
  }
}
