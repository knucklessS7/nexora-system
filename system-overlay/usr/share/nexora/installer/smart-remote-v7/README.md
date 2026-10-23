# Batocera Smart Remote V8.6 integrado

Interface V8.6 preservada. Energia removido. Uso somente na rede local.
Esta versão mantém as correções da instalação Aura confirmada pelo usuário e não exige P nem Enter na TV.

## Instalação
No pendrive preparado, a atualização é aplicada no próximo boot. Aguarde a instalação terminar e abra APPS → Smart Remote - Parear celular.
Em instalação manual: extraia este pacote no Batocera e execute Instalar.sh. O diagnóstico verifica Python, aiohttp, evdev, qrcode, pygame e uinput; o instalador valida o manifesto e o espaço para backup antes de alterar a instalação.
Código e configuração ficam em /userdata/system/batocera-smart-remote; serviço em /userdata/system/services/batocera_smart_remote. ROMs, BIOS, saves e configurações de outros aplicativos não são modificados. O instalador manual não cria atalhos de jogos.

## Pareamento
Ao abrir o painel na TV, PIN e QR aparecem automaticamente. O PIN dura 5 minutos e é de uso único. O QR contém somente a URL local /pair, sem PIN nem token. No celular conectado à mesma rede, digite os seis números. O backend valida o PIN e autoriza; o celular abre /control e o painel fecha.

O vínculo fica guardado de forma privada no Batocera por até um ano e é renovado durante o uso. Assim, fechar o site, perder a rede temporariamente ou reiniciar o serviço não exige outro PIN: basta abrir novamente o mesmo endereço no mesmo navegador do celular. O controle sempre libera os botões quando a página fecha ou a conexão cai. R revoga todos; Delete revoga o dispositivo selecionado. Revogar remove o vínculo e exige novo PIN.
Cinco tentativas por origem e vinte globais por janela de dois minutos. Host, Origin, cookie HttpOnly/SameSite, CSRF e WebSocket autenticado mantidos. HTTP local não é criptografado; nenhuma porta de roteador é aberta.
Se o IP antigo não existir mais, a inicialização seleciona o IPv4 privado atual e ajusta origem e sub-rede em memória. Troca de rede durante execução requer reiniciar o serviço.

## Controles
Home usa a integração Aura existente. Menu, OK, Voltar e direções enviam teclas; volume/play dependem da aplicação ativa. Mouse e texto usam a janela em foco. Somente apps locais registrados no ES são habilitados; sem comandos inventados. Nova abertura fica bloqueada enquanto houver um app ativo: use Home para fechar e voltar.
Gamepad: A/B/X/Y, direcional com troca dinâmica por arrasto contínuo, L1/L2/R1/R2, Start/Select, dois analógicos. L3/R3 são rótulos exclusivamente visuais: arraste a partir de qualquer ponto do analógico, inclusive o centro. Ambos podem ser usados simultaneamente. Tocar nas letras não envia cliques L3/R3. Configure Batocera Smart Remote Gamepad no menu de controles sem substituir o mapeamento dos outros dispositivos.
Personalizar permite conjunto/separado, mover, tamanho e espaçamento de grupos. Layout salvo no navegador por orientação. No horizontal, Recolher libera a área atrás do editor. O Safari pode exigir girar o aparelho manualmente. Proteções de toque longo foram preservadas; validação física iOS/Android continua pendente.

## Desinstalação e reversão
Execute bash /userdata/system/batocera-smart-remote/scripts/uninstall.sh. O serviço é parado e desabilitado; os arquivos são arquivados, não apagados. O marcador /userdata/system/batocera-smart-remote.disabled impede reinstalação pelo bootstrap USB. Instalar.sh remove esse marcador apenas em uma instalação explícita concluída.
Backups ficam em batocera-smart-remote.backup-DATA. Para reverter: pare o serviço, arquive a pasta atual, restaure a pasta de backup para batocera-smart-remote e copie scripts/batocera_smart_remote desse backup para /userdata/system/services/batocera_smart_remote. Depois habilite/inicie o serviço. Não altere outras pastas.

## Validação
Leia docs/VALIDACAO-V86.md. Evidências antigas em evidence/ são históricas, não provas da V8.6. Novas evidências ficam em evidence-v86/. O pacote foi preparado no Windows e os testes disponíveis usam Batocera 43.1 no QEMU. Não há homologação física desta atualização.
Para completar os testes reais, inicie o Batocera na mesma rede deste Windows, informe o IP e disponibilize acesso SSH autorizado. Celular físico e um jogo existente são necessários para testar Safari/Android e gameplay real.

## Analógicos: atualização radial
Arraste pela área circular, incluindo as letras L3/R3. Os rótulos são spans sem foco, cliques ou handlers, com pointer-events:none e user-select:none. O ponteiro fica capturado e pode atravessar o centro; dois dedos controlam os dois analógicos. A mudança solicitada remove os cliques centrais L3/R3 da interface, mantendo os códigos disponíveis no backend.
A zona morta radial padrão é 0.12. Para ajustar, defina `"analog_deadzone": 0.12` no objeto JSON do arquivo `/userdata/system/batocera-smart-remote/config.json` e reinicie o serviço. Intervalo aceito: 0 a 0.4. Fora da zona morta, a intensidade aumenta continuamente até 1. Não há uma segunda zona morta por eixo no dispositivo virtual; jogos podem aplicar ajustes próprios.
Rótulos não recebem foco. Botões interativos mantêm foco visível por teclado. O editor mantém os ajustes salvos e indica o analógico selecionado com um anel circular somente durante a personalização.
