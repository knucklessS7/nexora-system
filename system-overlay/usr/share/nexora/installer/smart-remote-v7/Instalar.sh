#!/bin/bash
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
if [ ! -t 0 ]; then
  export DISPLAY=${DISPLAY:-:0}
  exec xterm -T 'Instalar Batocera Smart Remote V8.6' -e bash "$0"
fi
bash "$HERE/scripts/install.sh"
batocera-services enable batocera_smart_remote
batocera-services start batocera_smart_remote
echo 'Instalado e iniciado. Abra Abrir pareamento.sh para conectar o celular.'
read -r -p 'Pressione Enter para fechar.' answer
