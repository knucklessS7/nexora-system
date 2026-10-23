#!/bin/bash
set -eu
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
BASE=/userdata/system/aura-neon-runtime
mkdir -p "$BASE"
exec >>"$BASE/install.log" 2>&1
echo "AURA NEON 8.1 $(date)"
[ ! -e /boot/AURA-NEON-DESATIVAR ] || exit 0
[ ! -e "$BASE/recovery-disabled" ] || exit 0
case "$(batocera-version)" in 43.1*|43u.1*|43u1*) ;; *) echo 'Versao nao suportada'; exit 1;; esac
[ "$(uname -m)" = x86_64 ]
[ ! -f "$BASE/v81.done" ] || exit 0
python3 "$HERE/install.py" "$HERE"
for SERVICE in aura7_native aura7_direct; do
 batocera-services disable "$SERVICE" || true
done
batocera-services enable aura_neon
touch "$BASE/enabled" "$BASE/v81.done"
echo 'Instalacao concluida; duas fileiras no proximo boot.'
# Tenta iniciar nesta sessao somente se o ES original ainda for o responsavel.
bash /userdata/system/services/aura_neon start &
