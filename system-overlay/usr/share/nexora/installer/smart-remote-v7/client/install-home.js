(() => {
  const button = document.querySelector('#installHome');
  const help = document.querySelector('#installHelp');
  if (!button || !help) return;
  let pending;
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const update = () => { button.hidden = standalone(); if (standalone()) help.hidden = true; };
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); pending = e; });
  window.addEventListener('appinstalled', () => { pending = null; button.hidden = true; help.hidden = true; });
  button.addEventListener('click', async () => {
    if (pending) {
      const prompt = pending; pending = null;
      try { await prompt.prompt(); await prompt.userChoice; return; } catch (_) { /* Show manual instructions below. */ }
    }
    const ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    help.textContent = ios
      ? 'No Safari, toque em Compartilhar e depois em Adicionar à Tela de Início. Confirme o nome Nexora Controle e toque em Adicionar.'
      : /Android/.test(navigator.userAgent)
        ? 'No menu ⋮ do Chrome, toque em Adicionar à tela inicial e confirme. Se aparecer Criar atalho, escolha essa opção.'
        : 'No celular: abra esta página no Safari (iPhone) ou Chrome (Android) e use o menu do navegador para adicionar à tela inicial.';
    help.textContent += ' O atalho usa esta rede e este endereço. Se o endereço do sistema mudar, escaneie novamente o QR Code.';
    help.hidden = false;
    button.setAttribute('aria-expanded', 'true');
  });
  matchMedia('(display-mode: standalone)').addEventListener('change', update);
  update();
})();
