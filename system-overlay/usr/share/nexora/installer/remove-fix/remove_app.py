"""Remove an explicitly selected Aura Flatpak; never interpret shortcut code."""
from pathlib import Path
import argparse,fcntl,json,os,re,shlex,subprocess,sys,time
import xml.etree.ElementTree as ET
BASE=Path('/userdata/system/aura-store-native')
ROOTS=[Path('/userdata/roms/apps'),Path('/userdata/roms/ports')]
ID=re.compile(r'[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2,}')

def identify(path):
    path=Path(path)
    if path.is_symlink() or path.parent not in ROOTS or not path.is_file() or path.stat().st_size>262144:return None
    text=path.read_text(encoding='utf-8-sig',errors='replace')
    if path.suffix.lower()=='.app':
        data=dict(s.split('=',1) for s in text.splitlines() if '=' in s and not s.startswith('#'))
        if not data.get('managed','').startswith('aura-flatpak-'):return None
        value=data.get('appid','')
        return value if ID.fullmatch(value) else None
    if path.suffix.lower()=='.sh' and '# aura-store-native-managed' in text:
        for line in text.splitlines():
            try:args=shlex.split(line)
            except ValueError:continue
            if args[:1]==['exec']:args=args[1:]
            if args[:2]!=['flatpak','run']:continue
            return next((a for a in args[2:] if ID.fullmatch(a)),None)
    return None

def scopes(appid):
    result=[]
    for scope in ('--user','--system'):
        p=subprocess.run(['flatpak','list',scope,'--app','--columns=application'],capture_output=True,text=True,timeout=60)
        if p.returncode:raise RuntimeError('Não foi possível consultar os aplicativos instalados.')
        if appid in p.stdout.splitlines():result.append(scope)
    return result

def remove(appid,selected=None):
    if not ID.fullmatch(appid):raise ValueError('Identificador inválido.')
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'reconcile.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        # Parse both XML files before changing any installed package.
        trees={r:ET.parse(r/'gamelist.xml') for r in ROOTS if (r/'gamelist.xml').exists()}
        if any(t.getroot().tag!='gameList' for t in trees.values()):raise RuntimeError('Lista de jogos inválida.')
        matches={r:[p for p in r.iterdir() if p.is_file() and identify(p)==appid] for r in ROOTS if r.is_dir()}
        with (BASE/'remove-app.log').open('a') as log:
            for scope in scopes(appid):
                p=subprocess.run(['flatpak','uninstall',scope,'--noninteractive','-y','--delete-data',appid],stdout=log,stderr=log,timeout=180)
                if p.returncode:raise RuntimeError('Desinstalação falhou; o atalho foi mantido. Consulte remove-app.log.')
        if scopes(appid):raise RuntimeError('O aplicativo ainda está instalado; remoção cancelada.')
        for root,paths in matches.items():
            names={p.name for p in paths}
            tree=trees.get(root)
            if tree is not None:
                for g in list(tree.getroot().findall('game')):
                    if (g.findtext('path') or '').removeprefix('./') in names:tree.getroot().remove(g)
                tmp=root/'gamelist.xml.remove-new';tree.write(tmp,encoding='utf-8',xml_declaration=True);os.replace(tmp,root/'gamelist.xml')
            for path in paths:
                path.unlink()
        report={'appid':appid,'installed':False,'removed_shortcuts':[str(p) for ps in matches.values() for p in ps],'time':time.time()}
        (BASE/'last-removal.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))

if __name__=='__main__':
    try:
        a=argparse.ArgumentParser();a.add_argument('--path');a.add_argument('--appid');args=a.parse_args()
        selected=Path(args.path) if args.path else None
        appid=identify(selected) if selected else args.appid
        if not appid:
            if selected is None or selected.parent not in ROOTS or selected.is_symlink() or selected.suffix not in ('.app','.sh'):
                raise ValueError('Atalho fora das pastas permitidas.')
            with (BASE/'reconcile.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                gl=selected.parent/'gamelist.xml'
                tree=ET.parse(gl) if gl.exists() else None
                selected.unlink()
                if tree is not None:
                    for g in list(tree.getroot().findall('game')):
                        if (g.findtext('path') or '').removeprefix('./')==selected.name:tree.getroot().remove(g)
                    tmp=gl.with_suffix('.remove-new');tree.write(tmp,encoding='utf-8',xml_declaration=True);os.replace(tmp,gl)
        else:remove(appid,selected)
    except Exception as e:
        BASE.mkdir(parents=True,exist_ok=True);(BASE/'remove-app-error.txt').write_text(str(e),encoding='utf-8')
        print(str(e),file=sys.stderr);sys.exit(1)
