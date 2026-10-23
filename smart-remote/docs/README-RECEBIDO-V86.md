# Batocera Smart Remote V8 — duas páginas (PIN → controle)

Interface original preservada, com backend Python e dispositivos Linux uinput. **Não é uma entrega homologada em hardware físico.** O fluxo foi exercitado em Batocera 43.1 x86_64 no QEMU e navegador Chromium desktop com viewports móveis. Android/iPhone, Wi-Fi real, reprodução nos navegadores e gameplay em emulador continuam pendentes.

## Instalação

Extraia este projeto no Batocera. No gerenciador de arquivos (F1), execute `Instalar.sh`, confirme com **s** e aguarde. Esse atalho instala, habilita e inicia o serviço. Depois execute `Abrir pareamento.sh`. Não execute o instalador no Windows.

Alternativa pelo terminal local ou SSH já configurado:

```sh
cd /caminho/do/projeto
bash scripts/doctor.sh
bash scripts/install.sh
```

O instalador pede confirmação, faz backup de instalação anterior e grava somente `/userdata/system/batocera-smart-remote` e `/userdata/system/services/batocera_smart_remote`. Não modifica ROMs, BIOS, gamelists, configurações de controles ou `custom.sh`. Não instala bibliotecas pela internet. Requer Python 3, aiohttp, evdev, qrcode, pygame e acesso a `/dev/uinput`; todos foram encontrados na VM 43.1. Texto remoto exige X11 + xdotool.

Revise `config.json`: `bind` é o IPv4 local; `networks` contém a sub-rede permitida; `origins` contém o endereço exato usado pelo celular. Reserve o IP no roteador. Se ele mudar, atualize os três campos. Em máquinas com várias interfaces, confira se a interface escolhida é a LAN confiável.

```sh
batocera-services enable batocera_smart_remote
batocera-services start batocera_smart_remote
bash /userdata/system/services/batocera_smart_remote status
```

O serviço aparece em Ajustes do sistema → Serviços após atualizar/reiniciar a interface. O nome usa sublinhados: hífens não são aceitos pelo mecanismo de serviços do Batocera. Habilitar controla o próximo boot; iniciar controla a sessão atual.

## Parear e usar

No gerenciador de arquivos do Batocera, execute `Abrir pareamento.sh` dentro da instalação, ou:

```sh
DISPLAY=:0 python3 /userdata/system/batocera-smart-remote/scripts/local_panel.py
```

1. Na TV, pressione **P** para abrir um PIN por 120 segundos.
2. No celular na mesma rede, leia o QR exibido na TV. O QR contém apenas a URL local `/pair`, sem senha.
3. O QR abre **somente a tela de PIN** (`/pair`), sem outro QR no celular. Digite o PIN. Na TV, confira o nome/IP da solicitação e pressione **Enter** para aprovar.
4. Após aprovação, o celular é redirecionado automaticamente a **`/control`**, a página exclusiva do controle (Menu, Gamepad, Mouse, Apps). Feche o painel local com **Esc** para controlar o EmulationStation. Enquanto ele está aberto, comandos remotos ficam suspensos para impedir aprovação por entrada remota.
5. Para revogar, reabra o painel: **R** revoga todos; setas escolhem uma sessão e **Delete** revoga apenas aquela. O painel indica se há controlador ativo.

O painel precisa de teclado local nesta versão. Não há overlay permanente durante jogos. Se o painel for encerrado abruptamente enquanto as entradas estiverem suspensas, reabra e feche normalmente; como alternativa local: `python3 scripts/local_panel.py revoke` e reinicie o serviço.

Um controlador ativo por vez, até oito sessões autorizadas. Novo pareamento não toma uma conexão ativa. Sessões expiram em oito horas e desaparecem ao reiniciar o serviço: será preciso parear novamente. O botão “Encerrar e revogar esta sessão” invalida o acesso atual.

## Controles

- **Menu:** setas, OK = Enter, Voltar = Escape, Menu = Espaço. Home/Energia ficam desabilitados, pois não existe integração comprovada para eles. Volume/play usam teclas multimídia; resposta depende do aplicativo.
- **Gamepad:** dispositivo `Batocera Smart Remote Gamepad`, disposição Xbox. A/B/X/Y, ombros, gatilhos, Start/Select, direcional e dois analógicos. Configure esse dispositivo pelo menu de controles do Batocera e escolha sua posição de jogador. O projeto não sobrescreve os controles existentes nem presume P1. Alguns emuladores exigem o dispositivo presente antes de abrir o jogo. Saída do jogo depende da hotkey configurada no Batocera.
- **Mouse:** arraste no touchpad; botões fazem clique e rolagem. Texto vai para a janela X11 em foco, nunca para shell executado pelo servidor. Não envie senhas em rede HTTP não confiável. Acentos/layout precisam de validação no navegador alvo.
- **Apps:** seis cartões originais preservados. Só ficam habilitados atalhos locais conhecidos e registrados no EmulationStation. Loja foi aberta pelo fluxo real. Streamings Aura exigem o runtime existente; não são instalados por este projeto. RGSX precisa estar instalado. O servidor usa a API ES exclusivamente em `127.0.0.1:1234`, sem ativar acesso público.

Tela cheia e rotação continuam best-effort. No iPhone pode ser necessário girar manualmente. A interface funciona sem orientação bloqueada. Não é anunciada como PWA offline.

## Segurança e manutenção

HTTP é o padrão de LAN: **não oferece confidencialidade**. Não encaminhe a porta no roteador. Não há UPnP ou dependência de nuvem. O servidor valida IP de origem, Host e Origin; PIN temporário com limite de tentativas, aprovação local, cookie HttpOnly/SameSite=Strict, token CSRF no handshake e logout, sequência crescente, tamanho e taxa de mensagens. Tokens são guardados apenas como hash na memória. Socket administrativo só é acessível localmente com permissões 0600; não existe rota web para aprovar/revogar outros dispositivos.

HTTPS opcional: configure `cert` e `key` como caminhos locais de um certificado confiável no celular; troque `origins` para `https://IP:8765`. Certificado deve incluir o IP/DNS usado no SAN. Instale a CA local confiável no aparelho por um procedimento administrativo próprio. Não ignore avisos de certificado. HTTPS e confiança Android/iOS ainda não foram testados nesta entrega.

Logs rotativos: `logs/server.log`; falha inicial: `logs/startup.log`. Não registram PIN nem tokens. Ao perder heartbeat por cerca de 2,5 segundos, desconectar ou revogar, botões/eixos são neutralizados. Não exponha o backend de teste à LAN: `--fake` aceita apenas bind loopback.

```sh
batocera-services restart batocera_smart_remote
batocera-services stop batocera_smart_remote
bash /userdata/system/batocera-smart-remote/scripts/uninstall.sh
```

A desinstalação desabilita o serviço e arquiva a instalação em `batocera-smart-remote.uninstalled-*`; não apaga dados dos jogos. Backups de atualização ficam em `batocera-smart-remote.backup-*`.

## Testes e fontes

Leia [a matriz de testes](docs/MATRIZ_DE_TESTES.md), [as limitações](docs/LIMITACOES.md) e [o progresso](PROGRESSO.md). Executar no Batocera:

```sh
python3 tests/test_remote.py
python3 tests/test_linux_e2e.py
```

O segundo teste requer instalação/serviço ativo, revoga sessões de teste e movimenta dispositivos reais; use somente em ambiente de validação. O primeiro usa adaptador fake e servidor HTTP local temporário. Evidências em `evidence/` distinguem esses ambientes.

Fontes: projeto V7 enviado pelo usuário (instruções originais em `docs/ORIGINAL-*`); [serviços do Batocera](https://wiki.batocera.org/scripting_services_rules_examples); [API do EmulationStation](https://wiki.batocera.org/es-webserver); scripts `/usr/bin/batocera-services` e `/index.html` do ES inspecionados na própria VM; bibliotecas instaladas aiohttp, evdev, qrcode e pygame. Nenhuma imagem/ícone de terceiros foi acrescentada: logo RGSX original preservada byte a byte.

## Alterações visuais e de navegação V8

- `client/index.html`: somente tela de PIN; acessível em `/` ou `/pair` pelo QR da TV. Não exibe QR falso.
- `client/pair.js`: solicita pareamento e consulta autorização na TV; só navega para `/control` depois de `approved=true`. Uma sessão já autorizada abre o controle sem PIN adicional.
- `client/control.html`: área de controles isolada, centralizada para celular, sem o formulário de PIN.
- `client/app.js`: permanece responsável por websocket, gamepad, mouse e aplicativos; botão **Sair** revoga sessão e volta ao PIN.
- `server/main.py`: protege `/control` exigindo cookie de sessão válido e libera publicamente só os arquivos de cliente necessários.
- O QR continua sendo gerado **somente pelo painel local** (`scripts/local_panel.py`); aponta para `/pair`, nunca fornece o PIN.
- Teste incluído para rota protegida, logout, ausência de QR na tela do celular.

**Importante:** o backend preservado ainda requer aprovação local com teclado, e o gamepad dentro de uma ROM continua dependendo de testes físicos. A interface não inventa modo demonstração nem autenticação simulada para produção.

## Ajuste visual V8.1 — direcional centralizado

Somente na aba **Menu / Controle principal**, o direcional (setas + OK) foi centralizado horizontalmente dentro do cartão, como num controle de TV. Os botões de volume e Play continuam na lateral direita, sem deslocar o direcional. O tamanho adapta-se a celulares menores. Gamepad, Mouse, Apps, login, backend e eventos não foram modificados.


## Atualização V8.2 — Gamepad personalizável

A tela **Gamepad** agora tem botão **⚙ Personalizar**. Em modo de edição, toque em uma seta, botão A/B/X/Y, gatilho L1/L2/R1/R2, Start, Select ou analógico e **arraste para mover**. Depois selecione o item e use **Tamanho** (60% a 185%). Escolha **Salvar** para aplicar, **Cancelar** para desfazer alterações não salvas, ou **Restaurar** para recuperar o layout original da orientação atual. Em telas horizontais, toque em **Recolher/Expandir** para tirar o painel da frente dos botões.

As alterações são salvas **somente no navegador deste celular** (localStorage), em perfis separados para **vertical e horizontal**. Cada celular pode ter seu layout sem interferir nos outros. Limpar os dados do site/navegador apaga o layout personalizado. Isso não cria sessão, não ignora o PIN e não precisa de alterações nos dispositivos Linux. Durante a edição, o frontend **não envia eventos dos controles selecionados** e neutraliza as entradas ao começar; fora da edição continuam valendo os comandos existentes. O modo foi testado no Chromium em ambiente isolado (arrastar, aumentar, salvar, recarregar, restaurar, modo vertical e horizontal), mas ainda precisa de validação em Android/iPhone reais e no Batocera físico.


Atualização V8.2.1: o direcional do gamepad agora é personalizado em conjunto (move e escala como um único bloco).


## V8.6 — Correção dos toques longos no iPhone

Foi aplicada proteção contra seleção de texto, menu Copiar/Buscar/Traduzir, menu contextual e arrasto nativo do navegador nas superfícies de controle. O CSS inclui `-webkit-user-select: none`, `-webkit-touch-callout: none`, `touch-action: none` e regras para filhos dos botões; o JavaScript bloqueia `contextmenu`, `selectstart` e `dragstart` nos controles.

O editor de layout, sliders e comandos do Batocera permanecem inalterados. A versão do CSS e JS no HTML foi incrementada para que o Safari não reutilize arquivos antigos do cache. Testar em iPhone/iPad físicos para confirmar o comportamento específico do Safari.
