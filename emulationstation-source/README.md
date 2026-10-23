# Alterações do EmulationStation

Estes arquivos registram as alterações nativas usadas pela interface Nexora sobre o EmulationStation do Batocera 43.

- `SystemView.cpp`: segunda fileira de aplicativos e integração com a Loja.
- `AuraMenuPanel.inc.cpp`: painel visual do menu principal. O nome interno `AuraMenuPanel` foi mantido para compatibilidade com a versão compilada.
- `SwitchComponent.cpp`: dimensionamento dos controles do menu temático.
- `remove-fix/AuraDelete.h`: remoção integrada dos atalhos gerenciados.

Use a árvore `batocera-emulationstation` correspondente ao Batocera 43. Aplique as mudanças nos arquivos equivalentes, acrescente a rota local `/aura/home` no `HttpServerThread.cpp`, compile pela cadeia oficial do Batocera e coloque o binário resultante nos diretórios `home-row`, `neon-v81`, `neon-v82`, `neon-v83` e `remove-fix` antes de gerar a imagem.

Os binários usados durante o desenvolvimento foram deliberadamente excluídos. Os manifests presentes no overlay correspondem à imagem pública testada e precisam ser regenerados após uma nova compilação.

As referências internas `/userdata/system/aura-*` e o identificador de tema `aura-7-native` são chaves de compatibilidade do sistema instalado; os textos visíveis são alterados para Nexora por `nexora-branding/apply.py`.
