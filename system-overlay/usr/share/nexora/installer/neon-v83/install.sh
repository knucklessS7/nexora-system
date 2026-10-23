#!/bin/bash
set -eu
BASE=/userdata/system/aura-neon-runtime
[ -d "$BASE" ] || exit 1
[ ! -e /boot/AURA-NEON-DESATIVAR ] || exit 0
[ ! -e "$BASE/recovery-disabled" ] || exit 0
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
python3 "$HERE/update.py" >>"$BASE/menu83-install.log" 2>&1
