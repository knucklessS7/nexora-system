# Batocera Smart Remote — Interface pronta, integração pendente

## O que está entregue
Frontend 100% estático em HTML, CSS e JavaScript, responsivo (celular e desktop), em português e sem dependências externas. Tem quatro áreas: controle de menus, gamepad com botões e dois analógicos, touchpad/teclado e atalhos para apps. Interface de pareamento PIN + área reservada ao QR Code. Eventos UI de pressionar/soltar, eixo, mouse, texto e apps passam por **uma função `transport(message)`** em `app.js`.

**Segurança:** este é um PROTÓTIPO. O PIN não autentica, o QR é apenas um marcador visual, não existe servidor, criptografia, sessão, nem comunicação com Batocera. Nunca expor como sistema funcional e nunca usar um PIN fixo.

## Rodar localmente
Abra `index.html` em navegador moderno. Para desenvolvimento, opcionalmente: `python3 -m http.server 8080` na pasta. Nenhuma instalação no Batocera é executada pelo protótipo.

## Contrato de eventos de frontend (proposta; Codex deve definir protocolo versionado)
```json
{"type":"button","control":"UP","phase":"down","seq":1,"ts":1760000000000}
{"type":"button","control":"UP","phase":"up","seq":2,"ts":1760000000001}
{"type":"axis","stick":"LEFT","x":0.5,"y":-0.3,"seq":3,"ts":1760000000002}
{"type":"mouse_move","dx":8,"dy":-3,"seq":4,"ts":1760000000003}
{"type":"type_text","text":"pesquisa","seq":5,"ts":1760000000004}
{"type":"launch_app","app":"YouTube","seq":6,"ts":1760000000005}
```
No protótipo, os eventos são emitidos localmente como `batocera-remote:demo-command`, sem envio para rede. O Codex deve vincular `transport()` a uma conexão autenticada; deixar visível o status real de conexão e receber confirmação/erro do servidor.

## Próximos passos obrigatórios para Codex
1. Criar servidor leve compatível com Batocera 43 e página servida na LAN, sem exposição pública.
2. Implementar pareamento **QR (URL local, sem token secreto de acesso) + PIN aleatório temporário exibido na TV**, limite de tentativas, aprovação local e sessão revogável. O botão da UI não deve dar acesso com PIN simulado. Definir estratégia real de apresentação do PIN/QR no EmulationStation sem quebrar a interface.
3. Autenticação de WebSocket, validação de origem, vínculo à sessão, CSRF nas rotas HTTP se aplicável, rate-limit; nenhum comando antes de autenticar. HTTPS local quando viável e com instruções de confiança/certificados, sem afirmar confidencialidade no HTTP.
4. Implementar adaptador Linux para menu EmulationStation, gameplay via uinput evdev conforme suporte real, hotkeys, múltiplas teclas simultâneas, analógicos, liberação de botões no disconnect, mouse, teclado e apps. Sem shell arbitrário a partir de payload do navegador.
5. Implementar catálogo de apps apenas instalados/configurados e mapa de comandos para Chromium/Firefox. Verificar aplicativos, binários e hardware antes de assumir suporte.
6. Criar serviço persistente em `/userdata/system/services/` de acordo com documentação efetiva da versão instalada, configuração persistente em `/userdata`, uninstaller e log. Evitar modificar partições somente-leitura e evitar depender de `custom.sh`.
7. Testar em browser desktop e mobile, reconexão, pareamento, PIN errado/expirado, revogação, duas conexões, latência, botões simultâneos, segurança e recuperação após reboot. Se sem acesso ao Batocera real, declarar testes reais pendentes e não afirmar “100% pronto”.
8. **Preservar identidade visual e estrutura**; ajustes de HTML/CSS mínimos quando integração exigir.

## Arquivos
- `index.html` — componentes e marcação
- `styles.css` — tema escuro sofisticado e responsivo
- `app.js` — interações locais demonstrativas e único ponto de integração
- `PROMPT_PARA_CODEX.txt` — instruções executáveis para Codex


## V2 — Gamepad horizontal e tela cheia
- Ao selecionar Gamepad em celulares, a interface **tenta** abrir em tela cheia e bloquear a orientação horizontal por meio de `requestFullscreen()` e `screen.orientation.lock('landscape')` quando suportados. **Não há garantia** em iPhone/Safari nem em todos os navegadores Android.
- O botão **Horizontal** permite tentar novamente após mudar permissões ou desbloquear a rotação.
- Em iPhones, geralmente será necessário girar manualmente o aparelho; a UI continua responsiva.
- Em telas horizontais pequenas com touchscreen, a interface oculta os demais painéis e usa praticamente toda a área disponível.
- **Sair** volta ao Menu e tenta desfazer orientação/travar tela cheia.
- `blur`, `visibilitychange` e `pagehide` liberam os comandos pressionados (eventos ainda locais em modo DEMO).
- O Codex deve implementar no backend um mecanismo obrigatório de *release-all* ao desconectar, perder WebSocket ou trocar de modo.
- O modo de visualização é intencionalmente demo, sem pareamento real, acesso remoto ou controle do Batocera.
- As APIs de orientação/tela cheia podem ser indisponíveis em `file://` ou HTTP simples fora de `localhost`; o Codex deve servir de forma apropriada.


## V3 — interface Soft Apps
- A grade de aplicativos foi ajustada para duas colunas, cartões discretos e identidade azul-marinho.
- Spotify foi substituído por Disney; Navegador por Loja; Jogos por RGSX.
- A logo visual do RGSX está em `assets/rgsx-logo.png`.
- Os valores `data-app` são identificadores propostos, não comandos de lançamento: o backend deve mapear explicitamente `Disney`, `Loja` e `RGSX` para aplicações presentes no Batocera. Não executar strings arbitrárias recebidas do navegador.
- O frontend continua demonstrativo, sem autenticação e integração reais.


## V4 — visual sem bordas
Retiradas as bordas de todos os seis cartões da aba Apps (YouTube, Disney, Netflix, Prime Video, Loja, RGSX) e do painel que os envolve. As demais abas, eventos e funções foram preservados. Mantido foco visível para teclado por acessibilidade.


## V5 - Logo RGSX sem fundo
A imagem `assets/rgsx-logo.png` tem canal alpha com fundo externo removido; os cartoes e os outros apps foram preservados.


## V6 — Emblema RGSX original enviado pelo usuário
O arquivo `assets/rgsx-logo.png` foi substituído pelo emblema original RG SX em PNG RGBA com fundo transparente, otimizado para carregamento no celular. Nenhuma alteração nos demais aplicativos, controles e integração pendente.


## V7 — ajuste visual
Os quatro ícones das abas Menu, Gamepad, Mouse e Apps foram substituídos por SVGs locais, sem bibliotecas externas. A integração e os demais recursos da V6 foram preservados.
