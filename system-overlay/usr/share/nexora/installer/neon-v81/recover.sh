#!/bin/bash
set -eu
mkdir -p /userdata/system/aura-neon-runtime
touch /userdata/system/aura-neon-runtime/recovery-disabled
batocera-services disable aura_neon || true
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as E
p=Path('/userdata/system/configs/emulationstation/es_settings.cfg')
t=E.parse(p)
for e in t.getroot().findall('string'):
 if e.get('name')=='ThemeSet':e.set('value','es-theme-carbon')
t.write(p,encoding='UTF-8',xml_declaration=True)
PY
echo 'AURA desativado. Reinicie pelo menu para usar o EmulationStation original.'
