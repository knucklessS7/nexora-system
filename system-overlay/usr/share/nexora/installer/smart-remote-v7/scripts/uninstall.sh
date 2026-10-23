#!/bin/bash
set -euo pipefail
BASE=/userdata/system/batocera-smart-remote
SERVICE=/userdata/system/services/batocera_smart_remote
[ ! -f "$SERVICE" ] || bash "$SERVICE" stop
batocera-services disable batocera_smart_remote
touch /userdata/system/batocera-smart-remote.disabled
# Preserve data in a clearly named archive, never delete ROMs/configs.
if [ -d "$BASE" ]; then
  if [ -f "$BASE/service.previous" ]; then cp "$BASE/service.previous" "$SERVICE"; else rm -f -- "$SERVICE"; fi
  mv -- "$BASE" "$BASE.uninstalled-$(date +%Y%m%d-%H%M%S)"
fi
echo 'Serviço removido; arquivos arquivados em /userdata/system/batocera-smart-remote.uninstalled-*.'
