#!/bin/bash
# Display the real installer failure, not old browser-session messages.
BASE=/userdata/system/aura
if [ "${1:-}" != --inside ] && command -v xterm >/dev/null 2>&1; then
  export DISPLAY="${DISPLAY:-:0}"
  exec xterm -title 'Aura - instalacao Chrome' -geometry 105x32 -e bash "$0" --inside
fi
echo 'AURA - INSTALACAO DO GOOGLE CHROME'
echo 'Mantenha a internet conectada. O download pode levar alguns minutos.'
echo 'Se falhar, fotografe as ultimas linhas desta janela.'
echo
LOG="$BASE/aura-firstboot.log"
START=0
[ ! -f "$LOG" ] || START=$(wc -l < "$LOG")
bash "$BASE/manual-install.sh" &
JOB=$!
tail --pid="$JOB" -n +"$((START+1))" -F "$LOG" 2>/dev/null &
TAIL=$!
wait "$JOB"
RC=$?
kill "$TAIL" 2>/dev/null || true
wait "$TAIL" 2>/dev/null || true
echo
echo "--- RESULTADO (codigo $RC) ---"
if flatpak info com.google.Chrome >/dev/null 2>&1; then
  echo 'Google Chrome instalado. Feche esta janela e abra um streaming.'
else
  echo 'Nao foi possivel consultar o Chrome. Diagnostico da ultima tentativa:'
  tail -n 45 "$LOG" 2>/dev/null
  echo 'Espaco disponivel:'
  df -h /userdata
fi
echo
read -r -p 'Pressione Enter para voltar ao menu. ' _
exit "$RC"
