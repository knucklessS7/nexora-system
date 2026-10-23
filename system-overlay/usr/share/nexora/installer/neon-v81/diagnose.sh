#!/bin/bash
# Exporta somente estado da interface; nao inclui perfis nem senhas de rede.
OUT=/userdata/system/aura-neon-runtime/diagnostico.txt
{
 date
 batocera-version
 echo '=== RESOLUCAO ==='
 DISPLAY=:0 xrandr --current 2>&1 | head -35
 echo '=== PROCESSO DA INTERFACE ==='
 ps -eo pid,args | grep -E 'emulationstation|aura7|aura-neon' | grep -v grep
 echo '=== TEMA E ARQUIVOS ==='
 python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as E
p=Path('/userdata/system/configs/emulationstation/es_settings.cfg')
try:
 for e in E.parse(p).getroot():
  if e.get('name') in ('ThemeSet','VideoMemory','ShowClock'):print(e.attrib)
except Exception as e:print(e)
for n in ('theme.xml','art/space.png','art/cards/apps.png','art/cards/ports.png'):
 p=Path('/userdata/themes/aura-7-native')/n
 print(str(p),p.stat().st_size if p.exists() else 'AUSENTE')
PY
 for LOG in /userdata/system/aura-neon-runtime/install.log /userdata/system/aura-neon-runtime/startup.log /userdata/system/aura-neon-runtime/session.log; do
  echo "=== $LOG ==="; tail -50 "$LOG" 2>/dev/null
 done
 echo '=== ERROS GRAFICOS ==='
 grep -Ei 'error|failed|texture|opengl' /userdata/system/configs/emulationstation/es_log.txt 2>/dev/null | tail -35
} > "$OUT" 2>&1
BOOT_WAS_RO=0
if awk '$2=="/boot" && $4 ~ /(^|,)ro(,|$)/ {found=1} END {exit !found}' /proc/mounts; then
 BOOT_WAS_RO=1
 mount -o remount,rw /boot || exit 1
fi
cp "$OUT" /boot/AURA-DIAGNOSTICO-INTERFACE.txt
sync
[ "$BOOT_WAS_RO" = 0 ] || mount -o remount,ro /boot
