#!/bin/bash
# Boot integration: installed files do not imply that the service is enabled/running.
set -eu
BASE=/userdata/system/aura-neon-runtime
exec >>"$BASE/ensure-start.log" 2>&1
date
[ ! -e /boot/AURA-NEON-DESATIVAR ] || exit 0
[ ! -e "$BASE/recovery-disabled" ] || exit 0
[ -e "$BASE/enabled" ] || { echo 'Aura disabled; refusing to override a new failure.'; exit 0; }
(cd "$BASE" && sha256sum -c binary.sha256) || exit 1
batocera-services enable aura_neon
if pgrep -f '^/userdata/system/aura-neon-runtime/bin/emulationstation( |$)' >/dev/null; then
  echo 'Aura already running';exit 0
fi
# Existing service validates original ES PID and performs one graceful takeover.
bash /userdata/system/services/aura_neon start
