(() => {
  'use strict';
  const banner = document.getElementById('connection-status');
  const connection = () => {
    if (!banner) return;
    banner.hidden = navigator.onLine !== false;
    banner.textContent = 'Sem conexão. Mantenha esta página aberta: seus campos ainda não enviados não foram salvos. Reconecte e envie o formulário.';
  };
  window.addEventListener('offline', connection);
  window.addEventListener('online', connection);
  connection();

  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/service-worker.js', {scope: '/', updateViaCache: 'none'})
      .catch(() => { /* Online forms remain usable if installation is unavailable. */ });
  }
  const installButton = document.getElementById('install-app');
  const installed = document.getElementById('installed-status');
  const unavailable = document.getElementById('install-unavailable');
  let prompt = null;
  const standalone = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (installed) installed.hidden = !standalone();
  if (unavailable) unavailable.hidden = window.isSecureContext;
  window.addEventListener('beforeinstallprompt', event => {
    if (!installButton || standalone()) return;
    event.preventDefault();
    prompt = event;
    installButton.hidden = false;
  });
  installButton?.addEventListener('click', async () => {
    if (!prompt) return;
    const current = prompt;
    prompt = null;
    installButton.hidden = true;
    try { await current.prompt(); await current.userChoice; } catch (_) { /* Menu instructions remain visible. */ }
  });
  window.addEventListener('appinstalled', () => {
    prompt = null;
    if (installButton) installButton.hidden = true;
    if (installed) installed.hidden = false;
  });

  let dirty = false;
  let submitting = false;
  const beforeLeave = event => {
    if (dirty && !submitting) { event.preventDefault(); event.returnValue = ''; }
  };
  document.querySelectorAll('form[method="post"]').forEach(form => {
    const isLogout = form.classList.contains('logout-form');
    const status = document.createElement('p');
    status.className = 'save-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.hidden = true;
    form.append(status);
    let busy = false;
    let timer;
    const changed = () => {
      if (isLogout || busy) return;
      dirty = true;
      window.addEventListener('beforeunload', beforeLeave);
      status.hidden = false;
      status.textContent = 'Alterações ainda não enviadas. Use o botão do formulário para confirmar.';
    };
    form.addEventListener('input', changed);
    form.addEventListener('change', changed);
    form.addEventListener('submit', event => {
      if (busy) { event.preventDefault(); return; }
      status.hidden = false;
      if (navigator.onLine === false) {
        event.preventDefault();
        status.textContent = 'Sem conexão: nada foi enviado. Mantenha a página aberta e envie quando a conexão voltar.';
        status.scrollIntoView({block: 'nearest'});
        return;
      }
      // Let beforeunload protect a dirty teaching form when signing out.
      // Do not lock logout: cancelling that browser dialog leaves the page open.
      if (isLogout) return;
      busy = true;
      submitting = true;
      form.setAttribute('aria-busy', 'true');
      status.textContent = 'Enviando… aguarde a confirmação do servidor.';
      // Do not disable fields: native form submission must include every value.
      timer = window.setTimeout(() => {
        status.textContent = 'O servidor ainda não confirmou. Aguarde; se o envio falhar, consulte o registro antes de repetir.';
      }, 15000);
    });
    window.addEventListener('pageshow', event => {
      busy = false;
      submitting = false;
      clearTimeout(timer);
      form.removeAttribute('aria-busy');
      if (event.persisted && !isLogout) {
        status.hidden = false;
        status.textContent = 'Formulário restaurado. Confira o registro antes de reenviar: ele pode já ter sido salvo.';
      }
    });
  });
  document.querySelectorAll('.table-scroll').forEach((region, index) => {
    const hint = document.createElement('p');
    hint.className = 'table-hint';
    hint.id = `table-hint-${index}`;
    hint.textContent = 'Deslize a tabela para os lados para ver todas as colunas.';
    region.before(hint);
    const update = () => {
      const scrolls = region.scrollWidth > region.clientWidth;
      hint.hidden = !scrolls;
      if (scrolls) {
        region.setAttribute('tabindex', '0');
        region.setAttribute('role', 'region');
        region.setAttribute('aria-label', 'Tabela com rolagem horizontal');
        region.setAttribute('aria-describedby', hint.id);
      } else {
        ['tabindex', 'role', 'aria-label', 'aria-describedby'].forEach(name => region.removeAttribute(name));
      }
    };
    update();
    if ('ResizeObserver' in window) new ResizeObserver(update).observe(region);
    else window.addEventListener('resize', update);
  });
})();
