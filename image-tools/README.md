# Ferramentas da imagem

Execute estes scripts em Linux/WSL como administrador. Eles exigem uma imagem desmontada e utilizam `losetup` para acessar as partições.

- `audit-image-privacy.sh IMAGEM.img`: procura estado de rede, perfis de navegador, sessões e chaves.
- `sanitize-mounted-share.sh /ponto/de/montagem`: remove estado pessoal de uma partição SHARE já montada. Faça backup antes.
- `compress-image.sh IMAGEM.img [SAIDA.img.gz]`: compacta para um arquivo temporário, testa o gzip e só então publica a saída.
- `validate-source.sh`: valida sintaxe e arquivos proibidos deste repositório.
