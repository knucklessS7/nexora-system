"""Explicit, offline shortcut installation. Never installs catalog entries at boot."""
from pathlib import Path
import fcntl,json,os,re,shlex,shutil,subprocess,sys,xml.etree.ElementTree as ET
BASE=Path('/userdata/system/aura-store-native');APPS=Path('/userdata/roms/apps')
def catalog():return json.loads((BASE/'catalog.json').read_text(encoding='utf-8'))['apps']
def entry(ident):
    a=next((a for a in catalog() if a['id']==ident and a['kind']=='aura_app'),None)
    if not a or not re.fullmatch(r'[a-z0-9_]+',a['runtime_id']):raise ValueError('Aplicativo fora do catálogo.')
    if Path(a['shortcut']).name!=a['shortcut']:raise ValueError('Nome de atalho inválido.')
    return a
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.aura-new');tmp.write_bytes(data);os.replace(tmp,path)
def install(ident):
    a=entry(ident);APPS.mkdir(parents=True,exist_ok=True)
    with (BASE/'reconcile.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        target=APPS/a['shortcut'];gl=APPS/'gamelist.xml'
        tree=ET.parse(gl) if gl.exists() else ET.ElementTree(ET.Element('gameList'))
        if target.exists():return
        command=shlex.join(['python3',str(BASE/'web_apps.py'),'launch',ident])
        atomic(target,('managed=aura-web-v1\nname='+a['name']+'\ntype=command\nexec='+command+'\n').encode())
        icon=BASE/'assets/icons'/(ident+'.png');image=APPS/'images'/('aura-'+ident+'.png')
        if icon.exists():image.parent.mkdir(exist_ok=True);shutil.copy2(icon,image)
        for g in list(tree.getroot().findall('game')):
            if (g.findtext('path') or '').removeprefix('./')==target.name:tree.getroot().remove(g)
        g=ET.SubElement(tree.getroot(),'game')
        for k,v in {'path':'./'+target.name,'name':a['name'],'desc':a['summary'],'image':str(image)}.items():ET.SubElement(g,k).text=v
        atomic(gl,ET.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True))
        deleted=BASE/'removed-shortcuts.json'
        if deleted.exists():
            rows=json.loads(deleted.read_text());rows=[x for x in rows if x!=str(target)];atomic(deleted,json.dumps(rows).encode())
def enforce_removed():
    with (BASE/'reconcile.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);_enforce_removed()
def _enforce_removed():
    deleted=BASE/'removed-shortcuts.json'
    if not deleted.exists():return
    rows=json.loads(deleted.read_text())
    for directory in (APPS,Path('/userdata/roms/ports')):
        names={Path(x).name for x in rows if Path(x).parent==directory and Path(x).suffix in ('.app','.sh')}
        for name in names:
            p=directory/name
            if p.is_file() and not p.is_symlink():p.unlink()
        gl=directory/'gamelist.xml'
        if gl.exists():
            tree=ET.parse(gl)
            for g in list(tree.getroot().findall('game')):
                if (g.findtext('path') or '').removeprefix('./') in names:tree.getroot().remove(g)
            atomic(gl,ET.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True))
def launch(ident):
    a=entry(ident);launcher=Path('/userdata/system/aura/streaming-native-v4/launch.sh')
    if not launcher.exists():raise RuntimeError('Runtime de streaming ausente. Consulte store-expansion.log.')
    os.execvp('bash',['bash',str(launcher),a['runtime_id']])
if __name__=='__main__':
    try:
        if sys.argv[1]=='install':install(sys.argv[2])
        elif sys.argv[1]=='launch':launch(sys.argv[2])
        elif sys.argv[1]=='enforce-removed':enforce_removed()
        else:raise ValueError('Ação desconhecida.')
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
