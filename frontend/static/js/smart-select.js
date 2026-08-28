(function () {
  'use strict';

  const state = {
    select: null,
    trigger: null,
    query: '',
    filters: {},
    filterDefs: [],
  };

  let layer;
  let titleEl;
  let searchEl;
  let filtersEl;
  let resultsEl;
  let countEl;
  let emptyEl;

  const FILTER_LABELS = {
    category: 'Categoría',
    vendor: 'Proveedor',
    status: 'Estado',
    stock: 'Disponibilidad',
    role: 'Rol',
    region: 'Región',
    channel: 'Canal',
    country: 'País',
    group: 'Grupo',
    area: 'Área',
  };

  function normalize(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function optionLabel(option) {
    return (option.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function fieldLabel(select) {
    if (select.dataset.smartTitle) return select.dataset.smartTitle;
    if (select.id) {
      const escapedId = window.CSS && typeof CSS.escape === 'function' ? CSS.escape(select.id) : select.id.replace(/[^a-zA-Z0-9_-]/g, '');
      const explicit = document.querySelector(`label[for="${escapedId}"]`);
      if (explicit) return explicit.textContent.replace(select.selectedOptions?.[0]?.textContent || '', '').trim() || explicit.textContent.trim();
    }
    const parentLabel = select.closest('label');
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true);
      clone.querySelectorAll('select,input,button,textarea').forEach(node => node.remove());
      const text = clone.textContent.replace(/\s+/g, ' ').trim();
      if (text) return text;
    }
    return select.getAttribute('aria-label') || select.name || 'Seleccionar opción';
  }

  function selectedText(select) {
    const option = select.selectedOptions && select.selectedOptions[0];
    return option ? optionLabel(option) : 'Seleccionar…';
  }

  function syncSelect(select) {
    const wrapper = select._smartSelectWrapper;
    if (!wrapper) return;
    const longestLabel = [...select.options].reduce((max, option) => Math.max(max, optionLabel(option).length), 0);
    wrapper.style.setProperty('--smart-select-width', `${Math.min(Math.max(longestLabel + 4, 12), 34)}ch`);
    const button = wrapper.querySelector('.smart-select-trigger');
    const text = wrapper.querySelector('.smart-select-trigger__text');
    if (text) text.textContent = selectedText(select);
    if (button) {
      button.disabled = select.disabled;
      button.setAttribute('aria-expanded', state.select === select ? 'true' : 'false');
      button.classList.toggle('is-placeholder', !select.value);
    }
  }

  function enhance(select) {
    if (!(select instanceof HTMLSelectElement) || select.dataset.smartSelectReady === '1') return;
    if (select.multiple || select.hasAttribute('data-native-select')) return;

    select.dataset.smartSelectReady = '1';
    select.classList.add('smart-select-native');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');

    const wrapper = document.createElement('span');
    wrapper.className = 'smart-select';
    wrapper.dataset.selectId = select.id || select.name || '';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'smart-select-trigger';
    button.setAttribute('role', 'combobox');
    button.setAttribute('aria-haspopup', 'dialog');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-label', fieldLabel(select));
    button.innerHTML = '<span class="smart-select-trigger__text"></span>';
    wrapper.appendChild(button);
    select.insertAdjacentElement('afterend', wrapper);
    select._smartSelectWrapper = wrapper;

    button.addEventListener('click', () => open(select, button));
    select.addEventListener('change', () => syncSelect(select));
    select.addEventListener('focus', () => open(select, button));
    select.addEventListener('invalid', () => open(select, button));
    syncSelect(select);
  }

  function alphaGroup(label) {
    const clean = normalize(label.replace(/^[A-Z]{1,8}-?\d+\s*[·:\-]?\s*/i, ''));
    const first = clean.charAt(0).toUpperCase();
    if (/[0-9]/.test(first)) return '0–9';
    if (first >= 'A' && first <= 'F') return 'A–F';
    if (first >= 'G' && first <= 'L') return 'G–L';
    if (first >= 'M' && first <= 'R') return 'M–R';
    if (first >= 'S' && first <= 'Z') return 'S–Z';
    return 'Otros';
  }

  function collectFilters(options) {
    const found = new Map();
    options.forEach(option => {
      Object.entries(option.dataset).forEach(([key, raw]) => {
        if (!key.startsWith('filter') || !raw) return;
        const name = key.slice(6);
        if (!name) return;
        const normalizedName = name.charAt(0).toLowerCase() + name.slice(1);
        if (!found.has(normalizedName)) found.set(normalizedName, new Set());
        found.get(normalizedName).add(raw);
      });
    });
    if (options.filter(o => o.value).length > 15 && found.size === 0) {
      const values = new Set(options.filter(o => o.value).map(o => alphaGroup(optionLabel(o))));
      if (values.size > 1) found.set('group', values);
    }
    return [...found.entries()]
      .filter(([, values]) => values.size > 1 && values.size <= 16)
      .map(([name, values]) => ({ name, label: FILTER_LABELS[name] || name, values: [...values] }));
  }

  function optionFilterValue(option, name) {
    if (!option.value) return '';
    if (name === 'group' && !option.dataset.filterGroup) return alphaGroup(optionLabel(option));
    const key = `filter${name.charAt(0).toUpperCase()}${name.slice(1)}`;
    return option.dataset[key] || '';
  }

  function buildFilterControls() {
    filtersEl.replaceChildren();
    state.filterDefs.forEach(def => {
      const group = document.createElement('fieldset');
      group.className = 'smart-select-filter';
      const legend = document.createElement('legend');
      legend.textContent = def.label;
      group.appendChild(legend);
      const choices = document.createElement('div');
      choices.className = 'smart-select-filter__choices';
      ['Todos', ...def.values].forEach(value => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'smart-select-filter__chip';
        button.textContent = value;
        const actual = value === 'Todos' ? '' : value;
        button.classList.toggle('active', (state.filters[def.name] || '') === actual);
        button.addEventListener('click', () => {
          state.filters[def.name] = actual;
          buildFilterControls();
          renderOptions();
        });
        choices.appendChild(button);
      });
      group.appendChild(choices);
      filtersEl.appendChild(group);
    });
    filtersEl.hidden = !state.filterDefs.length;
  }

  function visibleOptions() {
    if (!state.select) return [];
    const query = normalize(state.query);
    return [...state.select.options].filter(option => {
      const haystack = normalize(`${optionLabel(option)} ${option.value} ${Object.values(option.dataset).join(' ')}`);
      if (query && !haystack.includes(query)) return false;
      return state.filterDefs.every(def => {
        const expected = state.filters[def.name];
        return !expected || optionFilterValue(option, def.name) === expected;
      });
    });
  }

  function renderOptions() {
    const options = visibleOptions();
    resultsEl.replaceChildren();
    options.forEach(option => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'smart-select-option';
      button.disabled = option.disabled;
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', option.selected ? 'true' : 'false');

      const main = document.createElement('span');
      main.className = 'smart-select-option__main';
      main.textContent = optionLabel(option);
      button.appendChild(main);

      const metaValues = state.filterDefs
        .map(def => optionFilterValue(option, def.name))
        .filter(Boolean);
      if (metaValues.length) {
        const meta = document.createElement('span');
        meta.className = 'smart-select-option__meta';
        meta.textContent = [...new Set(metaValues)].join(' · ');
        button.appendChild(meta);
      }
      button.addEventListener('click', () => choose(option));
      resultsEl.appendChild(button);
    });
    const resultCount = options.filter(option => option.value).length;
    countEl.textContent = `${resultCount} ${resultCount === 1 ? 'resultado' : 'resultados'}`;
    emptyEl.hidden = options.length > 0;
  }

  function choose(option) {
    const select = state.select;
    if (!select || option.disabled) return;
    const changed = select.value !== option.value;
    select.value = option.value;
    syncSelect(select);
    if (changed) {
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
    close();
  }

  function open(select, trigger) {
    if (!layer || select.disabled) return;
    state.select = select;
    state.trigger = trigger;
    state.query = '';
    state.filters = {};
    state.filterDefs = collectFilters([...select.options]);
    titleEl.textContent = fieldLabel(select);
    searchEl.value = '';
    searchEl.placeholder = select.dataset.searchPlaceholder || 'Buscar por nombre, código o valor…';
    buildFilterControls();
    renderOptions();
    layer.hidden = false;
    layer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('smart-select-open');
    trigger.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => searchEl.focus());
  }

  function close() {
    if (!layer || layer.hidden) return;
    layer.hidden = true;
    layer.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('smart-select-open');
    if (state.select) syncSelect(state.select);
    const trigger = state.trigger;
    state.select = null;
    state.trigger = null;
    if (trigger && document.contains(trigger)) trigger.focus();
  }

  function buildLayer() {
    layer = document.createElement('div');
    layer.id = 'smart-select-layer';
    layer.className = 'smart-select-layer';
    layer.hidden = true;
    layer.setAttribute('aria-hidden', 'true');
    layer.innerHTML = `
      <div class="smart-select-backdrop" data-smart-close></div>
      <section class="smart-select-panel" role="dialog" aria-modal="true" aria-labelledby="smart-select-title">
        <header class="smart-select-header">
          <div><span class="smart-select-eyebrow">Selección avanzada</span><h2 id="smart-select-title"></h2></div>
          <button type="button" class="smart-select-close" data-smart-close aria-label="Cerrar">×</button>
        </header>
        <div class="smart-select-search-wrap">
          <span aria-hidden="true">⌕</span>
          <input id="smart-select-search" type="search" autocomplete="off" aria-label="Buscar opciones">
        </div>
        <div id="smart-select-filters" class="smart-select-filters"></div>
        <div class="smart-select-results-head"><strong>Opciones</strong><span id="smart-select-count"></span></div>
        <div id="smart-select-results" class="smart-select-results" role="listbox"></div>
        <div id="smart-select-empty" class="smart-select-empty" hidden>No hay opciones que coincidan con los filtros.</div>
      </section>`;
    document.body.appendChild(layer);
    titleEl = layer.querySelector('#smart-select-title');
    searchEl = layer.querySelector('#smart-select-search');
    filtersEl = layer.querySelector('#smart-select-filters');
    resultsEl = layer.querySelector('#smart-select-results');
    countEl = layer.querySelector('#smart-select-count');
    emptyEl = layer.querySelector('#smart-select-empty');
    layer.querySelectorAll('[data-smart-close]').forEach(node => node.addEventListener('click', close));
    searchEl.addEventListener('input', () => {
      state.query = searchEl.value;
      renderOptions();
    });
    searchEl.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        resultsEl.querySelector('.smart-select-option:not(:disabled)')?.focus();
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !layer.hidden) close();
    });
  }

  function scan(root) {
    if (root instanceof HTMLSelectElement) enhance(root);
    if (root.querySelectorAll) root.querySelectorAll('select').forEach(enhance);
  }

  function init() {
    buildLayer();
    scan(document);
    const observer = new MutationObserver(records => {
      records.forEach(record => {
        record.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
        });
        const owner = record.target instanceof HTMLOptionElement
          ? record.target.closest('select')
          : record.target instanceof HTMLSelectElement ? record.target : null;
        if (owner) syncSelect(owner);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  window.refreshSmartSelect = function (selectOrId) {
    const select = typeof selectOrId === 'string' ? document.getElementById(selectOrId) : selectOrId;
    if (select) {
      enhance(select);
      syncSelect(select);
    }
  };
  window.refreshAllSmartSelects = () => document.querySelectorAll('select').forEach(select => {
    enhance(select);
    syncSelect(select);
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
