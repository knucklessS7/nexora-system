#!/usr/bin/env python3
"""Install navigation corrections without replacing profiles or login data."""
import json
import hashlib
import os
from pathlib import Path

APPS = ('prime', 'netflix', 'disney', 'globoplay', 'spotify', 'apple_music', 'deezer', 'youtube', 'youtube_music')


def update(root=Path('/userdata'), source=None):
    source = source or Path(__file__).parent / 'controller-extensions'
    count = 0
    def put(path, data):
        nonlocal count
        if path.exists():
            old = path.read_bytes()
            if old == data:
                return
            backup = root / 'system/aura/backups/controller-v65' / path.relative_to(root)
            backup = backup.with_name(backup.name + '.' + hashlib.sha256(old).hexdigest()[:12])
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                backup.write_bytes(old)
        temp = path.with_name(path.name + '.aura-tmp')
        temp.write_bytes(data)
        os.replace(temp, path)
        count += 1
    for app in APPS:
        ext = root / 'system/dynamic/store-apps' / app / 'extension'
        manifest = ext / 'manifest.json'
        if not manifest.is_file():
            continue
        data = json.loads(manifest.read_text())
        put(ext / 'navigation.js', (source / app / 'navigation.js').read_bytes())
        put(ext / 'exit.js', (source / app / 'exit.js').read_bytes())
        if not (ext / 'controller-mode.js').exists():
            put(ext / 'controller-mode.js', b'globalThis.AURA_NATIVE_CONTROLLER = false;\n')
        for script in data.get('content_scripts', []):
            if 'navigation.js' in script.get('js', []) and 'controller-mode.js' not in script['js']:
                script['js'].insert(0, 'controller-mode.js')
        put(manifest, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
    ports=root/'roms/ports'
    ports.mkdir(parents=True,exist_ok=True)
    maintenance=root/'system/aura/maintenance'
    maintenance.mkdir(parents=True,exist_ok=True)
    for title,mode in [('Aura - Atualizar DRM Netflix','components'),('Aura - Conteudo protegido Netflix','settings')]:
        path=maintenance/(title+'.sh')
        if path.exists() and '# aura-drm-v66' not in path.read_text():
            continue
        put(path, ('#!/bin/bash\n# aura-drm-v66\nexec bash /userdata/system/aura/payload/streaming-launch.sh netflix '+mode+'\n').encode())
        path.chmod(0o755)
    repair=maintenance/'Aura - Reparar streaming.sh'
    if not repair.exists() or '/userdata/system/aura/' in repair.read_text():
        put(repair,b'#!/bin/bash\nexec bash /userdata/system/aura/payload/repair-visible.sh\n')
        repair.chmod(0o755)
    menu=ports/'Aura - Streamings.sh'
    if not menu.exists() or '# aura-streaming-menu-v70' in menu.read_text():
        put(menu,b'#!/bin/bash\n# aura-streaming-menu-v70\nexec python3 /userdata/system/aura/payload/streaming-menu.py\n')
        menu.chmod(0o755)
    import xml.etree.ElementTree as ET
    gamelist=ports/'gamelist.xml'
    tree=ET.parse(gamelist) if gamelist.exists() else ET.ElementTree(ET.Element('gameList'))
    if not any(e.findtext('path')=='./Aura - Streamings.sh' for e in tree.getroot().findall('game')):
        game=ET.SubElement(tree.getroot(),'game')
        ET.SubElement(game,'path').text='./Aura - Streamings.sh'
        ET.SubElement(game,'name').text='Aura - Streamings'
        put(gamelist,ET.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True))
    print('[CONTROLE] Navegacao Chrome v7.0:', count, 'arquivos atualizados.')


if __name__ == '__main__':
    update()
