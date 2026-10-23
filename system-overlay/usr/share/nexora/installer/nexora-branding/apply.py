"""Apply display branding only; retain integration paths and input identities."""
from pathlib import Path
import shutil, time, xml.etree.ElementTree as ET, ast, json

ROOT = Path('/userdata')
HERE = Path(__file__).resolve().parent
BACK = ROOT/'system/nexora-branding/backups'/time.strftime('%Y%m%d-%H%M%S')
changed = []

def save(path, data):
    old = path.read_bytes() if path.exists() else None
    if old == data: return
    target = BACK/path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): shutil.copy2(path, target)
    temp = path.with_name(path.name+'.nexora-tmp')
    temp.write_bytes(data)
    if path.exists(): shutil.copymode(path, temp)
    temp.replace(path)
    changed.append(str(path))

def labels(s):
    for a,b in [('Batocera Store Native · Aura','Loja'),('BATOCERA STORE','LOJA'),('Batocera Store','Loja'),('Batocera Aura','Nexora'),('BATOCERA SMART REMOTE','NEXORA REMOTE'),('Batocera Smart Remote','Nexora Remote'),('BATOCERA REMOTE','NEXORA REMOTE'),('AURA NATIVE · OFFLINE UI','NEXORA'),('AURA APP','APP'),('BIBLIOTECA AURA','BIBLIOTECA'),('SEU BATOCERA','SEU SISTEMA'),('A U R A','N E X O R A'),('F O R   B A T O C E R A',''),('AURA','NEXORA'),('Aura','Nexora'),('BATOCERA 43','NEXORA'),('BATOCERA','NEXORA'),('Batocera','Nexora')]:
        s=s.replace(a,b)
    return s

store=ROOT/'system/aura-store-native'
for name in ('neon.py','main.py','install.py'):
    p=store/name
    if not p.exists(): continue
    s=p.read_text()
    # Only display literals: never rename class names, wrapper paths or IDs.
    repl={'AURA':'NEXORA','BATOCERA STORE':'LOJA','SEU BATOCERA':'SEU SISTEMA','BIBLIOTECA AURA':'BIBLIOTECA','Aplicativos Linux para o seu Batocera.':'Aplicativos Linux para o seu sistema.','Batocera Aura':'Nexora','Criando atalho no Batocera...':'Criando atalho...','Batocera Store Native · Aura':'Loja','Batocera Store':'Loja','AURA NATIVE · OFFLINE UI':'NEXORA','AURA APP':'APP'}
    for a,b in repl.items(): s=s.replace(repr(a),repr(b))
    s=s.replace("'Batocera Store Native instalada em PORTS como Batocera Store.'","'Loja instalada em PORTS.'")
    ast.parse(s)
    save(p,s.encode())
remote=ROOT/'system/batocera-smart-remote'
mobile=HERE/'mobile'
if mobile.exists() and (remote/'client').is_dir():
    for src in mobile.rglob('*'):
        if src.is_file():
            dest=remote/'client'/src.relative_to(mobile)
            dest.parent.mkdir(parents=True,exist_ok=True)
            content=src.read_bytes()
            if src.suffix == '.html': content=labels(content.decode()).replace('\r\n','\n').encode()
            save(dest,content)
    p=remote/'server/main.py'
    if p.exists():
        s=p.read_text()
    else:
        s=None
    anchor="'styles.css','assets/rgsx-logo.png'"
    if s is not None and "'install-home.js'" not in s:
        if anchor in s:
            s=s.replace(anchor,anchor+",'install-home.js','manifest.webmanifest','assets/nexora-180.png','assets/nexora-192.png','assets/nexora-512.png'")
            ast.parse(s);save(p,s.encode())
        else:
            print('Rotas do controle não reconhecidas; arquivos Nexora foram preservados, sem alterar o servidor.')
for p in (remote/'client').glob('*.html'):
    s=p.read_text().replace('Configure Batocera Smart Remote Gamepad no Batocera antes de jogar.','Configure o gamepad virtual nos ajustes de controles antes de jogar.')
    save(p,labels(s).encode())
p=remote/'scripts/local_panel.py'
if p.exists():
    s=p.read_text().replace('Batocera Smart Remote — aprovação local','Nexora Remote — pareamento').replace('BATOCERA SMART REMOTE · V8.6','NEXORA REMOTE · V8.6')
    ast.parse(s);save(p,s.encode())
for theme in ('aura-neon','aura-7-native'):
    p=ROOT/'themes'/theme/'theme.xml'
    if p.exists():
        tree=ET.fromstring(p.read_bytes())
        for el in tree.iter('text'):
            if not list(el) and el.text: el.text=labels(el.text)
        save(p,ET.tostring(tree,encoding='utf-8',xml_declaration=True))
for folder in ('ports','apps'):
    p=ROOT/'roms'/folder/'gamelist.xml'
    if p.exists():
        tree=ET.fromstring(p.read_bytes())
        for game in tree.findall('game'):
            for tag in ('name','desc','developer'):
                el=game.find(tag)
                if el is not None and el.text: el.text=labels(el.text)
            for tag in ('image','thumbnail','marquee'):
                el=game.find(tag)
                if el is not None and el.text and el.text.endswith('/batocera-store-aura.png'):
                    icon=p.parent/'images/nexora-store.png'
                    icon.parent.mkdir(parents=True,exist_ok=True)
                    save(icon,(HERE/'nexora-logo.png').read_bytes())
                    el.text='./images/nexora-store.png'
        save(p,ET.tostring(tree,encoding='utf-8',xml_declaration=True))
p=store/'assets/aura-store-logo.png'
if p.exists(): save(p,(HERE/'nexora-logo.png').read_bytes())
for folder in ('ports','apps'):
    p=ROOT/'roms'/folder/'images/batocera-store-aura.png'
    if p.exists(): save(p,(HERE/'nexora-logo.png').read_bytes())
p=store/'catalog.json'
if p.exists():
    data=json.loads(p.read_text())
    for app in data.get('apps',[]):
        for key in ('name','summary','description'):
            if isinstance(app.get(key),str): app[key]=labels(app[key])
    save(p,(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({'changed':changed,'backup':str(BACK)},ensure_ascii=False,indent=2))
