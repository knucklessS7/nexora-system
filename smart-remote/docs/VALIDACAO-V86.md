# Diagnóstico V8.6 e validação

Recebido: manifesto desatualizado em README, PROGRESSO, app.js, control.html, gamepad-editor.js e styles.css; Power ainda no HTML; L3/R3 eram rótulos sem backend. Backend reintroduzia IP fixo, aprovação por teclado, Home desabilitado e abertura concorrente de apps.
Correções: reaproveitamento do backend Aura corrigido; PIN automático 300 s; rede dinâmica no início; serviço confirma prontidão; bloqueio de apps e Home; L3/R3 Linux BTN_THUMBL/BTN_THUMBR; Energia removido; manifesto regenerado; proteção contra reinstalação após desinstalar.
Logo RGSX e gamepad-editor.js preservados byte a byte do ZIP V8.6. Não foram criados comandos de lançamento nem instalados jogos ou dependências.

| Função | Implementado | Ambiente do teste | Resultado |
|---|---|---|---|
| Instalação e dependências | Sim | Batocera 43.1 QEMU | PASS |
| PIN/limites/sessão/origem/CSRF | Sim | HTTP/WS automatizado na VM | PASS, 4 testes |
| Concorrência de apps/Home | Sim | API ES simulada por teste na VM | PASS, 4 testes |
| A+L1+L3+R3 e analógico | Sim | uinput/evdev reais na VM | PASS |
| Mouse/roda/disconnect/watchdog/revogação | Sim | uinput/evdev reais na VM | PASS |
| Safari/iPhone e Android físicos | Sim | Não disponível | PENDENTE |
| Gameplay em jogos reais | Sim | Não disponível | PENDENTE: VM sem core/ROM de teste pronto |
| Reprodução Netflix/Prime/Disney | Atalhos existentes | Não disponível | PENDENTE; não é testada por evdev |

Nenhum teste de viewport ou evento sintético representa celular físico. Os testes existentes na pasta evidence/ pertencem a versões anteriores. Fontes: ZIP V8.6 do usuário, código local Aura anterior, diagnóstico físico previamente enviado, ambiente Batocera da VM. Nenhuma nova dependência externa.

## Resultados adicionais desta execução
- Chromium desktop com viewport móvel: PASS no PIN → controle, Loja real no ES, bloqueio de segunda abertura, Home fechando Loja e conexão mantida.
- PASS no toque D-pad+A simultâneo, direção inicial preservada ao deslizar, L3/R3 pressionar/soltar sem movimento acidental do analógico.
- PASS na edição individual e em grupo, tamanho e persistência após recarga, perfis retrato/paisagem distintos; editor não enviou comandos durante arrasto.
- PASS nos controles de seleção/contextmenu em Chromium. Não equivale a Safari físico.
- Linux uinput/evdev: 162 eventos observados, todos os botões, gatilhos, D-pad e ambos analógicos; teclado/multimídia/mouse/roda e liberação verificados. Texto digitado em aplicativo e efeitos de multimídia reais: pendentes nesta execução.
- Instalação/atualização e serviço start/status passaram. Desinstalação, reinstalação e reboot: revisão automática rejeitou a sequência, sem motivo detalhado além de blocked by policy; não executados. Sintaxe de instalação/desinstalação verificada na VM.
- Falhas dos testes de interface: editor sobrepunha A no horizontal (usado Recolher); harness tentou redimensionar janela em fullscreen (corrigido saindo de fullscreen). Reexecução passou. Não houve mudança estética para contornar o teste.
- Correções gráficas mínimas: botão Energia removido e grade de ações em três colunas; rótulos L3/R3 transformados em botões mantendo aparência. Logo e editor V8.6 preservados byte a byte.

## Atualização posterior: D-pad dinâmico
A solicitação nova substitui o requisito anterior de manter a direção inicial. O container agora captura o ponteiro e usa a posição atual para identificar a seta. Handoff envia up antes de down. Centro/espaço fora das setas neutraliza sem encerrar o gesto; reentrada funciona. Soltura/cancelamento/perda de captura/foco liberam a direção. Editor e outros botões mantêm seus ponteiros independentes.
Teste contínuo Chromium com eventos de toque pelo CDP e backend Batocera QEMU: PASS LEFT→UP, UP→RIGHT, RIGHT→DOWN, DOWN→LEFT; centro LEFT→RIGHT, UP→DOWN e LEFT→UP; A simultâneo; 20 transições rápidas; cancelamento e início no centro. Sequência exata WS e capturas em evidence-v86/dpad/. Primeira captura inspecionada visualmente: UP pressionado, LEFT liberado.
Safari/iPhone e Android físicos não disponíveis: continuam pendentes. Nenhuma afirmação de homologação física.

## Atualização: analógicos, L3/R3 e foco
Corrigidos: zona morta independente por eixo substituída por radial ajustável; X/Y enviados com um único SYN_REPORT; removidos flat/fuzz por eixo do uinput para não reintroduzir bloqueio nas diagonais. Frontend normaliza o vetor circular e calcula o deslocamento conforme tamanho/escala atuais. Rótulos L3/R3 mantidos centralizados, com área de clique circular de 24px, independente da captura dos analógicos. Sem contorno quadrado por toque; foco circular disponível via Tab. A primeira execução encontrou o clique central interceptando o início do gesto: a área foi reduzida e os testes de arrasto iniciam na área circular ao redor do rótulo, conforme operação documentada.

Resultados desta atualização:
- PASS Chromium/CDP com backend real Batocera 43.1 QEMU: círculos de 24 passos em cada analógico, quatro diagonais, normalização <= 1; posições alteradas e escalas 1.4/0.8 persistidas.
- PASS ambos analógicos simultâneos: valores evdev [22905, -22905, -22905, 22905]. Diagonal suave preservada: [19768, 2433, 0, 0].
- PASS L3 e R3 com ambos analógicos ativos: botão down/up sem novos comandos de eixo nem alteração dos valores. PASS retorno ao neutro ao soltar, blur e desconexão.
- PASS foco circular via teclado e ausência de outline/box-shadow no toque. Captura two-sticks-L3.png inspecionada visualmente: nenhum quadrado, rótulos centralizados, botões visuais deslocados nas diagonais.
- PASS regressão D-pad: quatro transições, passagem pelo centro, 20 trocas rápidas, cancelamento e botão A simultâneo.
- PASS 10 testes backend na VM (2 novos de mapeamento radial/SYN e 8 de autenticação/entradas/apps). Os testes matemáticos percorrem 360 ângulos, ambos os analógicos e deadzones 0/0.12/0.4.
- PASS sintaxe JavaScript.

Evidências: evidence-v86/analog/results.txt, backend-tests.txt e two-sticks-L3.png. Teste automatizado de gestos arquivado em evidence-v86/analog/test-analog.py (depende do harness QEMU local).
Pendentes: Safari/iPhone, Android físicos e reconhecimento dentro de jogos reais. Chromium com toque emulado e uinput/evdev na VM não comprovam esses ambientes físicos. Não foi executado novo ciclo de reboot nesta atualização.

## Revisão solicitada: L3/R3 exclusivamente visuais
Esta revisão substitui o clique central descrito nos testes históricos acima. HTML usa spans aria-hidden, sem tabindex/contenteditable/data-command ou handlers. CSS remove interação, seleção, callout e tap highlight dos rótulos. Os eventos chegam à superfície do analógico, inclusive ao começar sobre o texto. Removidas regras obsoletas dos antigos botões centrais. O editor aplicava seleção ao analog-group retangular: agora somente o círculo recebe o anel de seleção. Não foi necessário SVG: o destaque não reapareceu nos testes disponíveis.

Também removida a supressão genérica de foco nos gp-layout-item e limitada ao modo de edição a regra que apagava foco em A/B/X/Y e no direcional. Testes de Tab/foco em START, A e GP_UP confirmam outline visível.

PASS em Chromium com eventos de toque CDP -> WebSocket -> evdev no Batocera 43.1 QEMU: iniciar no centro de ambos, segurar 1100ms, arrastar em círculos/diagonais, multitouch; nenhum comando L3/R3, foco nos rótulos ou seleção textual; soltura, perda de foco e desconexão neutralizam eixos. Personalizar ligado: arrastar ambos os grupos pelo centro, sem comandos de jogo; anel circular, sem outline/box-shadow no wrapper; redimensionar/salvar e voltar a arrastar pelo centro funciona. Personalizar desligado: aparência inspecionada em capturas sem quadrado. Regressão D-pad passou. Fontes: código local do projeto e diagnóstico do usuário; nenhuma nova dependência.

Evidências desta revisão: evidence-v86/visual-labels/ (capturas, resultados e harness). Capturas LEFT-editor.png e RIGHT-held-center-drag.png inspecionadas visualmente. Testes anteriores de clique L3/R3 são históricos e não se aplicam aos spans atuais.

PENDENTE: Android e Safari/iPhone físicos, tanto com Personalizar ativo quanto inativo. Não estavam disponíveis. Toque CDP em Chromium não equivale a teste físico nem a Safari. Requer confirmar nesses dispositivos após atualizar o pendrive e reabrir a página. Jogos físicos também não foram executados.

## Atualização: dispositivo pareado lembrado
O token do navegador continua HttpOnly e não é exposto no QR. O Batocera passa a guardar apenas o hash do token, nome, datas e CSRF em `state/devices.json`, criado com permissão 0600 sob a instalação persistente. O token bruto só permanece no cookie do navegador. A validade é de um ano, renovada no máximo uma vez por dia para evitar escrita contínua no pendrive. Fechar a página continua liberando os controles; reabrir reconecta. Revogar um ou todos os dispositivos remove as entradas persistidas.

PASS: serviço real Batocera 43.1 no QEMU e Chromium com perfil móvel persistente. Exercitados PIN inicial, fechamento e reabertura do navegador, modo offline/online e reinício do serviço. O mesmo cookie retomou `/control` e o WebSocket sem novo PIN em todos os casos. Evidência: `evidence-v86/remember/results.txt`. Android e iPhone físicos permanecem pendentes.
