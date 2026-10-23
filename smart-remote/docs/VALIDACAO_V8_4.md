# V8.4 — toque longo e seleção nativa no iPhone

## Problema observado
O iPhone mostra o menu do Safari (Copiar, Buscar Seleção, Traduzir) sobre botões do Gamepad após toque prolongado.

## Correções aplicadas
- CSS: `-webkit-user-select: none`, `user-select: none`, `-webkit-touch-callout: none`, `-webkit-tap-highlight-color: transparent` nos controles e elementos internos.
- CSS: `touch-action: none` apenas nas superfícies ativas dos controles (direcional, face buttons, gatilhos, Start/Select e analógicos). Sliders e demais elementos do editor continuam normais.
- JS: previne `contextmenu`, `selectstart`, `dragstart` nas superfícies de controle; previne o toque nativo (`touchstart`) nas áreas de jogo, sem bloquear os controles de personalização.
- JS: limpa seleção de texto anterior ao começar a interação nos controles.
- Os links dos arquivos CSS/JS em `control.html` e CSS em `index.html` usam `?v=8.4` para ajudar a atualização de cache.

## Validações executadas
- `node --check client/app.js` e `node --check client/gamepad-editor.js` — passaram.
- `pytest -q tests/test_remote.py` — 4/4 testes passaram. Uma expectativa antiga do teste foi atualizada para `batocera-smart-remote-gamepad-v2`, já utilizado pela V8.3.
- Chromium mobile em ambiente isolado, com HTML/CSS/JS injetados: regras de `user-select:none` e `touch-action:none` confirmadas em direcional, A/B/X/Y, gatilhos, Start/Select e analógicos; eventos sintéticos de `contextmenu`, `selectstart` e `dragstart` cancelados; grupo A/B/X/Y selecionável, slider de espaço funcional, botão responde a press/release.

## O que ainda requer teste
- Safari **real** em iPhone/iPad (toque curto, toque longo, multitouch de dois dedos, personalização, troca de orientação).
- Batocera 43 físico, caso integração ainda não tenha sido validada neste ambiente.

A visualização no navegador de testes não substitui o teste em um iPhone físico. Use a V8.4 no servidor do Batocera e recarregue a página no Safari para verificar.
