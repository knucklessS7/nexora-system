#!/bin/bash
# Exporta somente estado da interface; nao inclui perfis nem senhas de rede.
mkdir -p /userdata/system/aura-neon-runtime
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
 echo '=== DEPENDENCIAS DO CONTROLE ==='
 python3 - <<'PYDIAG'
import importlib.util
from pathlib import Path
for name in ('pygame','qrcode','aiohttp','evdev'):
 try: print(name, bool(importlib.util.find_spec(name)))
 except Exception as exc: print(name,str(exc))
for path in ('/userdata/system/batocera-smart-remote/scripts/local_panel.py','/userdata/system/batocera-smart-remote/usb-install.done','/userdata/roms/apps/Smart Remote - Parear celular.app'):
 p=Path(path)
 print(path, 'exists='+str(p.exists()))
 if p.exists() and p.suffix=='.app':print(p.read_text())
PYDIAG
 echo '=== SERVICOS E BOOT ===' 
 ls -l /userdata/system/aura-neon-runtime/enabled /userdata/system/aura-neon-runtime/disabled-* /userdata/system/batocera-smart-remote/run/pid 2>/dev/null
 batocera-services list 2>/dev/null | grep -E 'aura|remote'
 for LOG in /userdata/system/aura/aura-bootstrap.log /userdata/system/aura-neon-runtime/ensure-start.log /userdata/system/aura/smart-remote-install.log /userdata/system/batocera-smart-remote/logs/startup.log /userdata/system/batocera-smart-remote/logs/panel.log /userdata/system/logs/es_launch_stderr.log; do
   echo "=== $LOG ==="; tail -35 "$LOG" 2>/dev/null
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
