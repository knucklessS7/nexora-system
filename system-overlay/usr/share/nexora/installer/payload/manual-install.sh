#!/bin/bash
set -e
BASE=/userdata/system/aura
if [ -d /tmp/aura-firstboot.lock ]; then
  echo "A instalacao Aura ja esta em andamento. Aguarde."
  exit 0
fi
rm -f "$BASE/state/complete" "$BASE/state/apps-streaming-v6.done" "$BASE/state/native-store-v6.done" "$BASE/state/native-store-v70.done"
exec bash "$BASE/firstboot.sh"
