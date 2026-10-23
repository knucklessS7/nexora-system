#!/bin/bash
set -euo pipefail
SOURCE=$(cd -- "$(dirname -- "$0")/.." && pwd)
BASE=/userdata/system/batocera-smart-remote
SERVICE=/userdata/system/services/batocera_smart_remote
if [ "${1:-}" != '--yes' ]; then
  echo 'Instala somente em /userdata, serviço desabilitado até você iniciar.'
  read -r -p 'Instalar Batocera Smart Remote? [s/N] ' answer
  [ "$answer" = s ] || exit 1
fi
bash "$SOURCE/scripts/doctor.sh"
python3 - "$SOURCE" <<'PYCHECK'
from pathlib import Path
import hashlib,json,shutil,sys
p=Path(sys.argv[1]);manifest=json.loads((p/'MANIFEST.sha256.json').read_text())
for rel,digest in manifest.items():
 f=(p/rel).resolve()
 assert f.is_relative_to(p.resolve()) and hashlib.sha256(f.read_bytes()).hexdigest()==digest,rel
base=Path('/userdata/system/batocera-smart-remote')
needed=sum(f.stat().st_size for f in p.rglob('*') if f.is_file())*2+8*1024*1024
if base.exists():needed+=sum(f.stat().st_size for f in base.rglob('*') if f.is_file())
if shutil.disk_usage('/userdata').free<needed:raise SystemExit('Espaco insuficiente para backup e atualizacao; instalacao atual preservada.')
PYCHECK
if [ -d "$BASE" ]; then
  [ ! -f "$SERVICE" ] || bash "$SERVICE" stop
  cp -a "$BASE" "$BASE.backup-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$BASE" /userdata/system/services
for folder in client server scripts docs; do cp -a "$SOURCE/$folder" "$BASE/"; done
cp "$SOURCE/Abrir pareamento.sh" "$BASE/"
chmod +x "$BASE/Abrir pareamento.sh"
if [ -f "$SERVICE" ] && ! grep -q 'BASE=/userdata/system/batocera-smart-remote' "$SERVICE"; then cp -a "$SERVICE" "$BASE/service.previous"; fi
cp "$SOURCE/scripts/batocera_smart_remote" "$SERVICE"
chmod +x "$SERVICE" "$BASE/scripts/"*.sh
if [ ! -f "$BASE/config.json" ]; then
 python3 - "$BASE" <<'PY'
import ipaddress,json,subprocess,sys
from pathlib import Path
rows=json.loads(subprocess.check_output(['ip','-j','-4','addr','show','scope','global']))
addresses=[a for r in rows for a in r['addr_info'] if ipaddress.ip_address(a['local']).is_private]
if not addresses:raise SystemExit('Sem IPv4 LAN. Configure a rede e execute novamente.')
a=addresses[0];ip=a['local'];network=str(ipaddress.ip_network(ip+'/'+str(a['prefixlen']),strict=False))
cfg={'bind':ip,'port':8765,'origins':['http://'+ip+':8765'],'networks':[network,'127.0.0.0/8']}
(Path(sys.argv[1])/'config.json').write_text(json.dumps(cfg,indent=2))
PY
fi
rm -f /userdata/system/batocera-smart-remote.disabled
echo 'Instalado. Confira config.json e habilite/inicie batocera_smart_remote em Serviços.'
echo "Painel na TV: DISPLAY=:0 python3 $BASE/scripts/local_panel.py"
