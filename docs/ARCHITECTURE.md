# Arquitetura

## Inicialização

`S30nexora-firstboot` roda a partir do sistema somente-leitura, copia o instalador para `/userdata/system/nexora-image`, aplica os componentes em ordem e registra `installed-v1`. O estado do usuário permanece na partição SHARE.

## Interface e Loja

Os diretórios `neon-v81`, `neon-v82` e `neon-v83` representam as etapas de tema e menus. `store-expansion` contém o catálogo ampliado e os logotipos. `nexora-branding` aplica a identidade final. `home-row`, `row-fix`, `remove-fix` e `hide-controller` cuidam da segunda fileira e da reconciliação dos atalhos instalados.

## Streaming

`payload/streaming-launch.sh`, `streaming-menu.py`, `controller-bridge.py` e `controller-extensions/` abrem o serviço web no Chrome, fecham uma sessão anterior quando necessário e traduzem os comandos do controle. Os aplicativos web não contêm credenciais.

## Controle remoto

O backend em `smart-remote/server/` usa `aiohttp` e cria dispositivos virtuais com `evdev/uinput`. `auth.py` controla PIN, tentativas, sessões lembradas e revogação. `inputs.py` envia teclado, mouse, botões e eixos. `apps.py` só permite atalhos descobertos no Batocera.

O frontend em `smart-remote/client/` implementa o controle principal, teclado, mouse e gamepad. O D-pad usa uma área única e troca a direção durante `pointermove`. Os dois analógicos calculam X/Y simultaneamente, aplicam zona morta radial e normalização circular.

## Limites

O grafo de código confirmou os módulos Python, JavaScript e testes do Smart Remote. Scripts, documentação e recursos estáticos foram conferidos diretamente porque esses diretórios não estavam indexados pelo analisador estrutural.
