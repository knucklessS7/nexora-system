# Compilação e empacotamento

## Pré-requisitos

- Árvore oficial do Batocera 43 x86_64 e sua cadeia de compilação.
- Linux com `bash`, `python3`, `squashfs-tools`, `util-linux`, `e2fsprogs` e `gzip`.
- Espaço livre suficiente para a árvore de compilação e uma imagem de aproximadamente 16 GB.

## Integração

1. Compile o Batocera 43 a partir do repositório oficial, conforme a documentação do projeto.
2. Antes de gerar o root filesystem final, copie o conteúdo de `system-overlay/` para a raiz do sistema de destino.
3. Preserve o modo executável de `etc/init.d/S30nexora-firstboot` e dos scripts `.sh`/serviços do instalador.
4. Integre os arquivos de `emulationstation-source/` à versão correspondente do EmulationStation e recompile. Copie o binário resultante para os componentes que possuem `emulationstation` em seus manifests e regenere os hashes. Binários de teste não são fonte e não estão neste repositório.
5. Gere a imagem normalmente pelo Batocera.
6. Monte a partição SHARE e aplique `current-release-overlay/` apenas quando os mesmos arquivos ainda não tiverem sido incorporados pelo instalador.
7. Execute `image-tools/audit-image-privacy.sh`, desmonte a imagem e compacte com `image-tools/compress-image.sh`.

## Primeiro boot limpo

Uma imagem pública não deve conter:

- `system/connman`, perfis NetworkManager ou chaves `wifi.*` pessoais;
- perfis Chrome, cookies, histórico, Local Storage, IndexedDB ou Service Worker;
- `system/batocera-smart-remote/state/devices.json`;
- chaves SSH, logs, downloads ou arquivos temporários;
- ROMs, BIOS ou saves do usuário.

O primeiro boot instala a Loja, o navegador e o pareamento. Streaming e aplicativos adicionais são obtidos pelo usuário pela Loja.
