/* Accesibilidad transversal de la SPA: foco, modales, etiquetas y anuncios. */
(function () {
  const focusableSelector = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])', 'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])'
  ].join(',');
  let lastModalTrigger = null;

  function visibleFocusable(root) {
    return Array.from(root.querySelectorAll(focusableSelector)).filter((el) =>
      !el.hidden && el.getAttribute('aria-hidden') !== 'true' && el.getClientRects().length > 0
    );
  }

  function prepareLabels(root) {
    root.querySelectorAll('label:not([for])').forEach((label) => {
      if (label.querySelector('input, select, textarea')) return;
      const field = label.parentElement?.querySelector('input, select, textarea');
      if (!field) return;
      if (!field.id) field.id = `a11y-field-${Math.random().toString(36).slice(2, 9)}`;
      label.htmlFor = field.id;
    });
  }

  function prepareModal(modal) {
    const card = modal.querySelector('.modal-card') || modal;
    if (card !== modal) {
      modal.removeAttribute('role');
      modal.removeAttribute('aria-labelledby');
    }
    card.setAttribute('role', 'dialog');
    card.setAttribute('aria-modal', 'true');
    card.setAttribute('tabindex', '-1');
    const title = card.querySelector('h1, h2, h3');
    if (title) {
      if (!title.id) title.id = `${modal.id || 'modal'}-a11y-title`;
      card.setAttribute('aria-labelledby', title.id);
    }
    modal.querySelector('.modal-backdrop')?.setAttribute('aria-hidden', 'true');
    prepareLabels(card);
  }

  function openModalA11y(modal) {
    if (modal.dataset.a11yOpen === 'true') return;
    modal.dataset.a11yOpen = 'true';
    lastModalTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modal.setAttribute('aria-hidden', 'false');
    const items = visibleFocusable(modal);
    requestAnimationFrame(() => (items[0] || modal.querySelector('.modal-card'))?.focus());
  }

  function closeModalA11y(modal) {
    if (modal.dataset.a11yOpen !== 'true') return;
    delete modal.dataset.a11yOpen;
    modal.setAttribute('aria-hidden', 'true');
    if (lastModalTrigger?.isConnected) requestAnimationFrame(() => lastModalTrigger.focus());
  }

  function syncModal(modal) {
    prepareModal(modal);
    if (modal.hidden) {
      modal.setAttribute('aria-hidden', 'true');
      closeModalA11y(modal);
    }
    else openModalA11y(modal);
  }

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const modal = Array.from(document.querySelectorAll('.modal:not([hidden])')).pop();
    if (!modal) return;
    const items = visibleFocusable(modal);
    if (!items.length) {
      event.preventDefault();
      return;
    }
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });

  window.opsA11yPageChanged = function (_id, title) {
    const status = document.getElementById('a11y-page-status');
    const main = document.getElementById('main-content');
    if (status) status.textContent = `Pantalla ${title} cargada`;
    if (main && document.documentElement.matches(':focus-within')) main.focus({ preventScroll: true });
  };

  document.addEventListener('DOMContentLoaded', () => {
    prepareLabels(document);
    document.querySelectorAll('.modal').forEach(syncModal);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.target.classList?.contains('modal')) syncModal(mutation.target);
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          if (node.classList.contains('modal')) syncModal(node);
          node.querySelectorAll?.('.modal').forEach(syncModal);
          prepareLabels(node);
        });
      });
    });
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['hidden'] });
  });
})();
