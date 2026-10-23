#!/bin/bash
set -euo pipefail
STAGE=${REMOTE_STAGE:-/boot/aura-installer/smart-remote-v7}
BASE=/userdata/system/batocera-smart-remote
[ ! -e /userdata/system/batocera-smart-remote.disabled ] || exit 0
mkdir -p /userdata/system/aura
exec >>/userdata/system/aura/smart-remote-install.log 2>&1
mkdir /tmp/aura-smart-remote-install.lock 2>/dev/null || exit 0
trap 'rmdir /tmp/aura-smart-remote-install.lock 2>/dev/null || true' EXIT
REVISION=$(sha256sum "$STAGE/MANIFEST.sha256.json" | cut -d ' ' -f 1)
if [ -f "$BASE/usb-install.done" ] && [ "$(cat "$BASE/usb-install.done")" = "$REVISION" ]; then
  batocera-services enable batocera_smart_remote
  bash /userdata/system/services/batocera_smart_remote start
  exit 0
fi
echo "Smart Remote: preparando instalação $(date)"
python3 - "$STAGE" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1])
for rel,digest in json.loads((p/'MANIFEST.sha256.json').read_text()).items():
 f=(p/rel).resolve()
 assert f.is_relative_to(p.resolve()) and hashlib.sha256(f.read_bytes()).hexdigest()==digest,rel
print('Manifesto verificado.')
PY
# Refresh the error-reporting panel even if the subsequent dependency check fails.
if [ -f "$BASE/scripts/local_panel.py" ]; then
 cp -f "$BASE/scripts/local_panel.py" "$BASE/scripts/local_panel.before-repair.py"
 cp -f "$STAGE/scripts/local_panel.py" "$BASE/scripts/local_panel.py"
fi
# Installation selects the currently available LAN, never the VM address.
for attempt in {1..60}; do
 if ip -4 -o addr show scope global | grep -q 'inet '; then break; fi
 sleep 2
done
bash "$STAGE/scripts/install.sh" --yes
batocera-services enable batocera_smart_remote
batocera-services start batocera_smart_remote
bash /userdata/system/services/batocera_smart_remote status
python3 - <<'PY'
from pathlib import Path
import shutil,time
p=Path('/userdata/roms/apps/Smart Remote - Parear celular.app')
p.parent.mkdir(parents=True,exist_ok=True)
data='managed=aura-smart-remote-v7\nname=Smart Remote - Parear celular\ntype=command\nexec=python3 /userdata/system/batocera-smart-remote/scripts/local_panel.py\n'
if p.exists() and p.read_text()!=data:
 b=Path('/userdata/system/batocera-smart-remote')/('shortcut-backup-'+str(time.time_ns())+'.app');shutil.copy2(p,b)
p.write_text(data)
import xml.etree.ElementTree as ET
image=Path('/userdata/system/batocera-smart-remote/client/assets/pairing.png')
gl=p.parent/'gamelist.xml'
tree=ET.parse(gl) if gl.exists() else ET.ElementTree(ET.Element('gameList'))
items=[g for g in tree.getroot().findall('game') if (g.findtext('path') or '').removeprefix('./') in (p.name,str(p))]
game=items[0] if items else ET.SubElement(tree.getroot(),'game')
for duplicate in items[1:]:tree.getroot().remove(duplicate)
for key,value in {'path':'./'+p.name,'name':'Smart Remote - Parear celular','image':str(image),'thumbnail':str(image),'marquee':str(image)}.items():
 node=game.find(key)
 if node is None:node=ET.SubElement(game,key)
 node.text=value
if gl.exists():shutil.copy2(gl,Path('/userdata/system/batocera-smart-remote')/'apps-gamelist.before-icon.xml')
tmp=gl.with_suffix('.remote-new');tree.write(tmp,encoding='utf-8',xml_declaration=True);tmp.replace(gl)
PY
printf '%s\n' "$REVISION" > "$BASE/usb-install.done"
curl -fsS --max-time 3 http://127.0.0.1:1234/reloadgames >/dev/null || true
echo 'Smart Remote instalado; abra APPS > Smart Remote - Parear celular.'
