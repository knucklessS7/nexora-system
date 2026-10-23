# Nexora System

Código-fonte das personalizações do Nexora para Batocera 43 x86_64.

Este repositório contém a camada criada para o Nexora: interface, Loja, atalhos de streaming, pareamento e controle pelo celular, integração de primeiro boot, tema, instaladores e ferramentas de auditoria da imagem. A imagem pronta para gravação continua disponível no [site oficial de download](https://nexora-download-oficial.marcianascimen658034.chatgpt.site/).

## Componentes

- `smart-remote/`: backend HTTP/WebSocket, painel de PIN/QR, controle, mouse, teclado, gamepad virtual, frontend móvel, instalação, desinstalação e testes.
- `system-overlay/`: arquivos copiados para o sistema durante a criação da imagem. O serviço `S30nexora-firstboot` instala a camada persistente no primeiro boot.
- `emulationstation-source/`: fontes das alterações nativas da interface e instruções para recompilar o binário.
- `current-release-overlay/`: pequenos arquivos da versão pública atual aplicados por último na partição SHARE.
- `download-site/`: página estática do download público.
- `image-tools/`: scripts portáveis para auditorar, sanitizar e compactar uma imagem antes da publicação.
- `docs/`: arquitetura, compilação e limites de redistribuição.

## O que não está no repositório

A imagem `.img`/`.img.gz`, o sistema-base compilado, o binário modificado do EmulationStation, runtimes Flatpak, perfis do Chrome, cookies, sessões pareadas, redes Wi-Fi, logs e caches não pertencem ao código-fonte publicado. O sistema-base pode ser obtido no projeto [Batocera.linux](https://github.com/batocera-linux/batocera.linux). O RGSX permanece no [repositório original](https://github.com/RetroGameSets/RGSX).

Os arquivos `emulationstation` usados nos testes eram binários compilados e foram omitidos. As alterações correspondentes estão em `emulationstation-source/` e devem ser recompiladas a partir do código-fonte correspondente do Batocera/EmulationStation.

## Instalação do controle remoto

No Batocera 43, copie `smart-remote/` para um diretório temporário e execute:

```bash
bash smart-remote/Instalar.sh
```

O instalador grava somente em `/userdata`, cria o serviço `batocera_smart_remote` e preserva ROMs, BIOS e saves. A desinstalação segura fica em `smart-remote/scripts/uninstall.sh`.

## Geração da imagem

Leia [docs/BUILD.md](docs/BUILD.md). A ordem do primeiro boot é definida em `system-overlay/etc/init.d/S30nexora-firstboot`. A árvore `system-overlay/` deve ser incorporada ao root filesystem durante a compilação, mantendo permissões e nomes de arquivo.

## Segurança e privacidade

Antes de publicar uma imagem, execute os scripts de `image-tools/` e confira manualmente a partição SHARE. O repositório não contém credenciais conhecidas nem estado persistente de usuário. O controle remoto é destinado a uma rede local confiável e não abre portas no roteador.

## Testes

```bash
python3 -m unittest discover -s smart-remote/tests -p 'test_*.py'
bash image-tools/validate-source.sh
```

Os testes de integração Linux/uinput precisam ser executados dentro do Batocera. Android, iPhone, rede, Bluetooth e jogos físicos devem ser homologados em hardware real.

## Licença

O código próprio do Nexora é publicado sob GPL-3.0-or-later. Marcas, ícones, fontes e componentes de terceiros mantêm suas licenças e titulares originais; consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
