#!/bin/bash
set -eu
BASE=/userdata/system/aura
PAYLOAD="$BASE/payload"
THEME=/userdata/themes/aura-neon
STATE="$BASE/state/neon-v80.done"
if [ -f "$STATE" ]; then exit 0; fi
BACK="$BASE/backups/neon-v80-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACK" "$BASE/state" "$THEME"
CONF=/userdata/system/configs/emulationstation/es_settings.cfg
[ ! -f "$CONF" ] || cp -p "$CONF" "$BACK/es_settings.cfg"
if [ -d /userdata/system/aura-store-native ]; then cp -a /userdata/system/aura-store-native "$BACK/store"; fi
for SRC in /usr/share/emulationstation/themes/es-theme-carbon /usr/share/emulationstation/themes/carbon; do
  if [ -d "$SRC" ]; then cp -a "$SRC"/. "$THEME"/; break; fi
done
cp -a "$PAYLOAD/aura-neon"/. "$THEME"/
python3 "$THEME/build_cards.py" "$THEME"
mkdir -p /userdata/system/aura-store-native
cp -a "$PAYLOAD/native-store"/. /userdata/system/aura-store-native/
chmod +x /userdata/system/aura-store-native/launch.sh
python3 /userdata/system/aura-store-native/install.py
python3 - "$CONF" <<'PY'
import sys,os,xml.etree.ElementTree as ET
from pathlib import Path
p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
t=ET.parse(p) if p.exists() else ET.ElementTree(ET.Element('config'))
r=t.getroot()
for typ,key,val in [('string','ThemeSet','aura-neon'),('bool','ShowClock','true')]:
 e=next((x for x in r.findall(typ) if x.get('name')==key),None)
 if e is None:e=ET.SubElement(r,typ,{'name':key})
 e.set('value',val)
tmp=p.with_suffix('.neon.tmp');t.write(tmp,encoding='UTF-8',xml_declaration=True);os.replace(tmp,p)
PY
touch "$STATE"
echo "[AURA NEON] Tema e loja instalados. Backup: $BACK"
