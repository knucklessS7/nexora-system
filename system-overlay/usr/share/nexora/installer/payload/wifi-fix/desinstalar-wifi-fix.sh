#!/bin/bash
set -eu
BASE=/userdata/system/aura-wifi
touch "$BASE/disabled"
batocera-services disable aura_wifi
python3 "$BASE/wifi.py" restore
if [ -f /userdata/system/services/aura_wifi ] && grep -q '# aura-wifi-managed' /userdata/system/services/aura_wifi; then
  rm -f /userdata/system/services/aura_wifi
fi
echo "Ajuste desativado. Backups preservados. Reinicie para concluir."
