# Ajuste de Wi-Fi — Batocera 43.1 / Aura

Este pacote prioriza `LUIS AUGUSTO_2.4G` e desativa AutoConnect apenas de `#CLARO-WIFI`. Não define IP fixo. A senha é lida somente dos arquivos locais já configurados; não aparece em comandos, logs nem neste pacote.

## Instalação no seu pendrive

O instalador Aura copia e ativa este pacote automaticamente no próximo boot, antes de tentar instalar os navegadores. Aguarde alguns minutos com a rede residencial ligada. A execução só ocorre dentro do Batocera; não execute os `.sh` no Windows.

Para executar manualmente no terminal do Batocera:

```bash
bash /boot/aura-installer/payload/wifi-fix/instalar-wifi-fix.sh
```

O serviço `aura_wifi` é registrado pelo comando nativo `batocera-services` em `/userdata/system/services/aura_wifi`. Há um único serviço e um bloqueio contra execuções simultâneas. Cada execução faz no máximo três tentativas. Depois disso, o próprio ConnMan fica responsável pela reconexão automática; o script não fica em loop.

## Diagnóstico e comportamento

Antes de alterar a conexão, registra versão, SSID realmente associado obtido com `iw`, interfaces, IPv4, rota, estado/Favorite/AutoConnect/Immutable dos dois perfis e teste HTTPS. O diagnóstico não imprime `batocera.conf` nem propriedades que possam conter senhas.

Se a rede de casa já tiver IP e rota, não a desconecta. Outros SSIDs escolhidos manualmente são preservados. Somente a rede pública Claro é desconectada. Para perfis favoritos, usa a API oficial do ConnMan para alterar AutoConnect. Para provisionamentos imutáveis da Claro, remove somente as seções correspondentes em arquivos locais graváveis de `/userdata` ou `/var/lib/connman`, com backup. Arquivos de `/boot` e a imagem do sistema não são modificados pelo ajuste Wi-Fi.

Se faltarem credenciais reutilizáveis no ConnMan, lê a senha da rede residencial em `batocera.conf`, `batocera-boot.conf` ou perfis locais. Prepara um arquivo nativo ConnMan com DHCP, protegido com permissão 600 em `/userdata/system/aura-wifi/home.config`, e um link no armazenamento de execução do ConnMan. Se não encontrar a senha, pede configuração local pelo menu; não pede senha nesta conversa.

O serviço persistente é necessário para o caso relatado de a Claro voltar a ser escolhida após reiniciar: ele reaplica a política quando os perfis são recriados e recupera a conexão com limite de tentativas. Não reinicia o ConnMan nem chama `batocera-wifi enable`, que reiniciaria o serviço nesta versão.

O ConnMan inicia antes do serviço de recuperação. Se o perfil público for recriado por outra configuração em cada boot, pode haver associação breve antes de a política ser reaplicada. O diagnóstico lista as origens dos provisionamentos para identificar essa situação. Um perfil imutável gerado por arquivo somente de `/boot` será preservado e pode exigir ajuste adicional após análise do log; não há garantia de bloqueio desse caso sem a validação física.

## Verificar

```bash
bash /userdata/system/aura-wifi/verificar-wifi.sh
```

O log fica em `/userdata/system/aura-wifi/wifi.log`. O diretório e os backups são restritos (700/600) e podem conter credenciais locais: não compartilhe os backups. Somente o log de diagnóstico foi preparado para não exibir senha.

## Desinstalar e recuperar

```bash
bash /userdata/system/aura-wifi/desinstalar-wifi-fix.sh
```

Desativa o serviço, restaura AutoConnect anterior dos perfis presentes, restaura seções removidas da Claro se ainda não existirem e remove o link gerenciado de provisionamento residencial. Não substitui o `batocera.conf` inteiro, para preservar alterações posteriores. Os backups ficam em `/userdata/system/aura-wifi/backups`. O marcador `disabled` impede que o Aura reinstale automaticamente. Instalar manualmente remove esse marcador.

Se houver uma operação em andamento, aguarde terminar e repita a desinstalação. Perfis não presentes no momento precisam voltar a aparecer para que seu AutoConnect original seja restaurado. O arquivo `autoconnect-original.json` permanece disponível para repetir a restauração. Reinicie depois de desinstalar.

## Verificação realizada e pendente

A imagem do próprio pendrive foi lida sem modificá-la: versão 43.1, scripts `S08connman`, `S04populate`, `S99userservices`, `batocera-services` e `batocera-wifi`. Confirmados os serviços persistentes e o comportamento de recriação de provisionamentos. Confirmado também o caminho Flatpak compilado `/userdata/saves/flatpak/binaries`, que faltava no ajuste de certificados anterior.

Não foi possível consultar a conexão Wi-Fi ativa nem a partição Linux de dados a partir deste Windows. A associação real à Claro, a existência dos perfis e o estado da persistência serão verificados no próximo boot, antes das mudanças. A relação entre o portal Claro e a recusa TLS é uma hipótese, não uma causa confirmada.

Testes automatizados usam arquivos e ConnMan simulados; não substituem validação física. Conferir: boot normal; reinício pelo menu; desligamento completo; ambas as redes presentes; rede residencial temporariamente ausente; retorno do sinal. Em cada teste, confirmar SSID com `iw`, IP e rota DHCP e HTTPS. Não declarar sucesso apenas pela tela do menu ou pela existência do atalho.

## Fontes

- [Batocera: scripts e serviços](https://wiki.batocera.org/launch_a_script)
- [ConnMan: API de serviços](https://raw.githubusercontent.com/aldebaran/connman/master/doc/service-api.txt)
- [ConnMan: provisionamento](https://raw.githubusercontent.com/aldebaran/connman/master/doc/config-format.txt)
- [OSTree: certificados por repositório](https://ostreedev.github.io/ostree/man/ostree.repo-config.html)

Os arquivos Wi-Fi não modificam jogos, BIOS, saves, temas ou aplicativos. O pacote Aura separado inclui a correção solicitada para localizar os certificados no armazenamento real do Flatpak.
