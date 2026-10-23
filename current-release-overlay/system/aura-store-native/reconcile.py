#!/usr/bin/env python3
"""Reconcile only identified Aura launchers; retain unrelated PORTS files."""
from pathlib import Path
import copy, fcntl, json, os, re, shlex, shutil, subprocess, time
import xml.etree.ElementTree as ET

USER=Path('/userdata')
BASE=USER/'system/aura-store-native'
APPS=USER/'roms/apps'; PORTS=USER/'roms/ports'
MARK='aura-flatpak-v6.4'

def metadata(path):
    text=path.read_text(encoding='utf-8-sig')
    return dict(line.split('=',1) for line in text.splitlines() if '=' in line and not line.startswith('#'))

def flatpak_id(data):
    if data.get('appid'): return data['appid']
    try:
        args=shlex.split(data.get('exec',''))
        if args[:2]==['flatpak','run']:
            return next((a for a in args[2:] if not a.startswith('-')),None)
    except ValueError: pass
    return None

def list_installed():
    rows={}
    for scope in ['--user','--system']:
        p=subprocess.run(['flatpak','list',scope,'--app','--columns=application,name'],capture_output=True,text=True,timeout=60)
        if p.returncode: raise RuntimeError('Falha ao listar Flatpaks; limpeza cancelada.')
        for line in p.stdout.splitlines():
            parts=line.split('\t'); appid=parts[0].strip()
            if not re.fullmatch(r'[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+',appid): continue
            rows[appid]=(parts[1].strip() if len(parts)>1 else appid,scope)
    return rows

def tree(path):
    result=ET.parse(path) if path.exists() else ET.ElementTree(ET.Element('gameList'))
    if result.getroot().tag!='gameList': raise ValueError('Gamelist invalida: '+str(path))
    return result

def xmlbytes(t): return ET.tostring(t.getroot(),encoding='utf-8',xml_declaration=True)
def relname(value): return (value or '').removeprefix('./')

class Changes:
    def __init__(self):
        self.back=USER/'system/aura-store-backup'/('apps-v6.4-'+str(time.time_ns()))
        self.entries=[]
    def save(self,path):
        dest=self.back/path.relative_to(USER)
        if path.exists() and not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    def write(self,path,content,mode=None):
        if isinstance(content,str): content=content.encode('utf-8')
        if path.exists() and path.read_bytes()==content: return
        existed=path.exists();self.save(path);path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(path.name+'.aura-tmp');tmp.write_bytes(content)
        if mode is not None: tmp.chmod(mode)
        elif existed: shutil.copymode(path,tmp)
        os.replace(tmp,path)
        self.entries.append({'path':str(path),'action':'replace' if existed else 'create'})
    def archive(self,path):
        self.save(path);path.unlink();self.entries.append({'path':str(path),'action':'archive'})
    def finish(self):
        if self.entries:
            self.back.mkdir(parents=True,exist_ok=True)
            (self.back/'changes.json').write_text(json.dumps(self.entries,indent=2),encoding='utf-8')
            print('Backup e registro: '+str(self.back))

def reconcile(rows=None):
    # AURA removed shortcut priority
    from web_apps import enforce_removed
    enforce_removed()
    BASE.mkdir(parents=True,exist_ok=True)
    lock=(BASE/'reconcile.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX)
    rows=list_installed() if rows is None else rows
    # Validate BOTH lists before any file is removed or replaced.
    at=tree(APPS/'gamelist.xml');pt=tree(PORTS/'gamelist.xml')
    changes=Changes();APPS.mkdir(parents=True,exist_ok=True)
    catalog={}
    if (BASE/'catalog.json').exists():
        catalog={a['appid']:a for a in json.loads((BASE/'catalog.json').read_text())['apps'] if a.get('appid')}
    canonical={};removed_apps=set();removed_ports=set()
    for appid,(name,scope) in sorted(rows.items()):
        if appid=='org.videolan.VLC': continue  # Preserve original v6.3 exclusion for root.
        meta=catalog.get(appid,{})
        args=list(meta.get('run_args',[]) or (['--no-sandbox'] if appid in ['org.chromium.Chromium','com.google.Chrome','com.discordapp.Discord'] else []))
        if appid=='com.google.Chrome':
            for flag in ['--test-type','--disable-features=Translate,TranslateUI','--lang=pt-BR','--no-first-run','--no-default-browser-check','--disable-session-crashed-bubble','--hide-crash-restore-bubble','--noerrdialogs','--disable-infobars']:
                if flag not in args: args.append(flag)
        path=APPS/(appid+'.app')
        if path.exists() and not metadata(path).get('managed','').startswith('aura-flatpak-'):
            print('Atalho pessoal preservado: '+path.name);continue
        name=(meta.get('name') or name).replace('\n',' ')
        cmd=shlex.join(['flatpak','run',scope,appid]+args)
        changes.write(path,f'managed={MARK}\nname={name}\ntype=command\nappid={appid}\nexec={cmd}\n')
        canonical[appid]=path
        games=[g for g in at.getroot().findall('game') if relname(g.findtext('path'))==path.name]
        game=games[0] if games else None
        if game is None:
            # Preserve scraped metadata and favorites from a managed legacy alias.
            for old in APPS.glob('*.app'):
                data=metadata(old)
                if old!=path and data.get('managed','').startswith('aura-flatpak-') and flatpak_id(data)==appid:
                    prior=next((g for g in at.getroot().findall('game') if relname(g.findtext('path'))==old.name),None)
                    if prior is not None: game=copy.deepcopy(prior);at.getroot().append(game);break
        if game is None: game=ET.SubElement(at.getroot(),'game')
        for duplicate in games[1:]: at.getroot().remove(duplicate)
        for k,v in {'path':'./'+path.name,'name':name+' (Flatpak)','desc':meta.get('summary') or name,'genre':meta.get('category') or 'Aplicativos'}.items():
            node=game.find(k)
            if node is None: node=ET.SubElement(game,k)
            node.text=v
        if game.find('image') is None:
            roots=[USER/'saves/flatpak/binaries/exports/share/icons/hicolor',USER/'saves/flatpak/data/.local/share/flatpak/exports/share/icons/hicolor']
            icons=[f for root in roots if root.is_dir() for f in root.rglob(appid+'.*') if f.is_file() and f.suffix.lower() in ['.png','.svg','.jpg']]
            if icons:
                icon=max(icons,key=lambda f:f.stat().st_size)
                dest=APPS/'images'/(appid+icon.suffix)
                changes.write(dest,icon.read_bytes())
                ET.SubElement(game,'image').text='./images/'+dest.name
    # Archive old Aura Flatpak aliases only after the replacement exists.
    streams={}
    for path in sorted(APPS.glob('*.app'),key=lambda p:(p.name!=metadata(p).get('name','')+'.app',p.name)):
        data=metadata(path);managed=data.get('managed','')
        if managed.startswith('aura-flatpak-'):
            appid=flatpak_id(data)
            if appid and appid not in rows:
                changes.archive(path);removed_apps.add(path.name);continue
            if appid=='org.chromium.Chromium' and appid not in rows and 'com.google.Chrome' in canonical:
                changes.archive(path);removed_apps.add(path.name);continue
            if appid in canonical and path!=canonical[appid]: changes.archive(path);removed_apps.add(path.name)
        elif managed.startswith('batocera-dynamic-completo'):
            cmd=data.get('exec','')
            if cmd in streams: changes.archive(path);removed_apps.add(path.name)
            elif cmd: streams[cmd]=path
    for path in PORTS.glob('*.sh'):
        if path.stat().st_size>262144: continue
        text=path.read_text(errors='replace')
        remove=False
        if '# aura-streaming-v6' in text:
            for cmd in streams:
                if ('exec bash "'+cmd+'"') in text and Path(cmd).is_file(): remove=True
        elif '# aura-store-native-managed' in text:
            for appid in canonical:
                if re.search(r'(?<![\w.-])'+re.escape(appid)+r'(?![\w.-])',text): remove=True
        if remove: changes.archive(path);removed_ports.add(path.name)
    for t,removed in [(at,removed_apps),(pt,removed_ports)]:
        seen=set()
        for game in list(t.getroot().findall('game')):
            name=relname(game.findtext('path'))
            if name in removed or (name and name in seen): t.getroot().remove(game)
            else: seen.add(name)
    runner=USER/'system/aura-app-runner.sh'
    changes.write(runner,'#!/bin/bash\nexec python3 /userdata/system/aura-store-native/app_runner.py "$@"\n',0o755)
    cfg=ET.ElementTree(ET.Element('systemList'));system=ET.SubElement(cfg.getroot(),'system')
    for k,v in {'name':'apps','fullname':'APPS','path':str(APPS),'extension':'.app .APP','command':str(runner)+' %ROM%','platform':'pc','theme':'apps'}.items(): ET.SubElement(system,k).text=v
    changes.write(USER/'system/configs/emulationstation/es_systems_aura_apps.cfg',xmlbytes(cfg))
    changes.write(APPS/'gamelist.xml',xmlbytes(at));changes.write(PORTS/'gamelist.xml',xmlbytes(pt))
    changes.finish()
    print(f'APPS: {len(canonical)} Flatpaks; duplicados arquivados: {len(removed_apps)+len(removed_ports)}.')

if __name__=='__main__': reconcile()
