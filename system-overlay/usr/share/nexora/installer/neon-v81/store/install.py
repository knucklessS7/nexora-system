#!/usr/bin/env python3
from pathlib import Path
import xml.etree.ElementTree as ET, shutil, time
BASE=Path('/userdata/system/aura-store-native')
PORTS=Path('/userdata/roms/ports'); IMAGES=PORTS/'images'; GAMELIST=PORTS/'gamelist.xml'
BACK=Path('/userdata/system/aura-store-backup')/('native-v1-'+str(time.time_ns())); BACK.mkdir(parents=True,exist_ok=True)
PORTS.mkdir(parents=True,exist_ok=True); IMAGES.mkdir(parents=True,exist_ok=True)
for p in [PORTS/'Batocera Store Native.sh', PORTS/'Dynamic Store.sh', PORTS/'DynamicStore.sh']:
    try:
        if p.exists(): shutil.copy2(p,BACK/p.name); p.unlink()
    except Exception: pass
shortcut=PORTS/'Batocera Store.sh'
if shortcut.exists():
    try: shutil.copy2(shortcut,BACK/shortcut.name)
    except Exception: pass
shortcut.write_text('#!/bin/bash\n# aura-store-native-entry\nexec bash /userdata/system/aura-store-native/launch.sh\n',encoding='utf-8',newline='\n'); shortcut.chmod(0o755)
svg='''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#39daff"/><stop offset="1" stop-color="#ab60ff"/></linearGradient></defs><rect width="600" height="600" rx="120" fill="#07121f"/><circle cx="300" cy="300" r="205" fill="#0d2f4b" stroke="url(#g)" stroke-width="20"/><path d="M185 390 300 155 415 390h-66l-24-54h-54l-24 54zm110-111h6l-3-8z" fill="url(#g)"/></svg>'''
(IMAGES/'batocera-store-aura.svg').write_text(svg,encoding='utf-8')
if GAMELIST.exists():
    try: tree=ET.parse(GAMELIST); root=tree.getroot()
    except Exception: root=ET.Element('gameList'); tree=ET.ElementTree(root)
else: root=ET.Element('gameList'); tree=ET.ElementTree(root)
for g in list(root.findall('game')):
    name=(g.findtext('name') or '').strip().lower(); path=(g.findtext('path') or '').strip().lower()
    if 'batocera store' in name or 'dynamic store' in name or 'store native' in name or path.endswith('/batocera store native.sh'):
        root.remove(g)
rel='./'+shortcut.name
g=ET.SubElement(root,'game')
vals={'path':rel,'name':'Batocera Store','desc':'Aplicativos, jogos e streaming em um só lugar. Navegue pelo controle ou teclado. Conecte-se à internet para instalar aplicativos.','developer':'Batocera Aura','genre':'Aplicativos','image':'./images/batocera-store-aura.svg','thumbnail':'./images/batocera-store-aura.svg'}
for k,v in vals.items():
    e=ET.SubElement(g,k); e.text=v
tree.write(GAMELIST,encoding='UTF-8',xml_declaration=True)
print('Batocera Store Native instalada em PORTS como Batocera Store.')
