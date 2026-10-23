#!/usr/bin/env python3
"""Bounded, local-only ConnMan repair for this Batocera installation."""
from pathlib import Path
import configparser, fcntl, json, os, re, shutil, subprocess, sys, time

HOME_SSID='LUIS AUGUSTO_2.4G'
BLOCK_SSID='#CLARO-WIFI'
BASE=Path('/userdata/system/aura-wifi')
STORE=Path('/var/lib/connman')
RUNTIME=STORE/'aurahome.config'
CONF=Path('/userdata/system/batocera.conf')

def log(message):
    text=time.strftime('%Y-%m-%d %H:%M:%S')+' '+message
    print(text, flush=True)
    BASE.mkdir(parents=True,exist_ok=True)
    with (BASE/'wifi.log').open('a',encoding='utf-8') as f: f.write(text+'\n')

def run(args,seconds=20):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=seconds)
        return r.returncode,r.stdout
    except (OSError,subprocess.TimeoutExpired): return 99,''

def read_settings(path):
    values={}
    if path.is_file():
        for line in path.read_text(errors='replace').splitlines():
            if line.lstrip().startswith(('#',';')) or '=' not in line: continue
            key,value=line.split('=',1); values[key.strip()]=value.strip()
    return values

def read_ini(path):
    c=configparser.ConfigParser(interpolation=None,strict=False)
    c.optionxform=str
    try: c.read(path,encoding='utf-8')
    except (configparser.Error,OSError): pass
    return c

def local_password():
    # Values never enter the command line, stdout, logs or deliverables.
    for path in [CONF,Path('/boot/batocera-boot.conf')]:
        values=read_settings(path)
        for prefix in ['wifi','wifi2','wifi3','wifi.hidden']:
            if values.get(prefix+'.ssid')==HOME_SSID and values.get(prefix+'.key'):
                return values[prefix+'.key'].replace('\\','')
    paths=list(STORE.glob('wifi_*/settings'))
    paths+=list(STORE.glob('*.config'))
    paths+=[Path('/userdata/system/network-connman.config')]
    for path in paths:
        cfg=read_ini(path)
        for section in cfg.sections():
            if cfg.get(section,'Name',fallback='')==HOME_SSID:
                value=cfg.get(section,'Passphrase',fallback='')
                if value: return value
    return None

def atomic(path,text,mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        os.chmod(tmp,mode); f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def backup_file(path):
    directory=BASE/'backups'; directory.mkdir(parents=True,exist_ok=True)
    os.chmod(directory,0o700)
    dest=directory/(path.name+'.original')
    if path.is_file() and not dest.exists():
        shutil.copy2(path,dest); os.chmod(dest,0o600)

def provision():
    key=local_password()
    if not key:
        log('Credencial residencial nao localizada. Configure a rede de casa localmente no menu do Batocera.'); return False
    if '\n' in key or '\r' in key:
        log('Formato de credencial nao suportado; configure localmente no menu.'); return False
    target=BASE/'home.config'
    if RUNTIME.exists() or RUNTIME.is_symlink():
        if not RUNTIME.is_symlink() or RUNTIME.resolve()!=target.resolve():
            log('Existe uma configuracao aurahome de outra origem; preservada.'); return False
    # A normal ConnMan provisioning file: DHCP, no invented static address.
    text='[service_aurahome]\nType=wifi\nName='+HOME_SSID+'\nPassphrase='+key+'\nIPv4=dhcp\n'
    if not target.exists() or target.read_text()!=text:
        backup_file(target); atomic(target,text)
    if not RUNTIME.is_symlink(): RUNTIME.symlink_to(target)
    log('Credencial local reutilizada pelo ConnMan (valor omitido).')
    return True

def remove_public_provisioning():
    """Remove only Claro stanzas from writable local provisioning files."""
    statefile=BASE/'provisioning-original.json'
    state=json.loads(statefile.read_text()) if statefile.exists() else {}
    for link in STORE.glob('*.config'):
        path=link.resolve()
        if not path.is_file(): continue
        if not (path.is_relative_to('/userdata') or path.is_relative_to(STORE)):
            continue  # Never modify /boot, /etc or the read-only system image.
        cfg=read_ini(path)
        names=[s for s in cfg.sections() if s.startswith('service_') and cfg.get(s,'Name',fallback='')==BLOCK_SSID]
        if not names: continue
        import io
        for section in names:
            state.setdefault(str(path),{}).setdefault(section,dict(cfg[section]))
        atomic(statefile,json.dumps(state))
        backup_file(path)
        for section in names: cfg.remove_section(section)
        out=io.StringIO(); cfg.write(out)
        # Keep symlink target inode so ConnMan's file watcher sees the change.
        with path.open('w',encoding='utf-8') as f: f.write(out.getvalue()); f.flush(); os.fsync(f.fileno())
        log('Removido somente provisionamento da rede publica Claro; backup restrito salvo.')

class Connman:
    def __init__(self):
        import dbus
        self.dbus=dbus; self.bus=dbus.SystemBus()
        self.manager=dbus.Interface(self.bus.get_object('net.connman','/'),'net.connman.Manager')
    def services(self): return self.manager.GetServices(timeout=10)
    def service(self,path): return self.dbus.Interface(self.bus.get_object('net.connman',path),'net.connman.Service')
    def auto(self,path,value): self.service(path).SetProperty('AutoConnect',self.dbus.Boolean(value),timeout=10)
    def scan(self):
        for path,props in self.manager.GetTechnologies(timeout=10):
            if props.get('Type')=='wifi' and props.get('Powered'):
                try: self.dbus.Interface(self.bus.get_object('net.connman',path),'net.connman.Technology').Scan(timeout=20)
                except Exception: pass

def save_auto(path,props):
    file=BASE/'autoconnect-original.json'
    data=json.loads(file.read_text()) if file.exists() else {}
    if str(path) not in data:
        data[str(path)]={'name':str(props.get('Name','')),'auto':bool(props.get('AutoConnect',False))}
        atomic(file,json.dumps(data,indent=2))

def set_auto(cm,path,props,value):
    if bool(props.get('AutoConnect'))==value: return
    if props.get('Immutable'):
        log('Perfil '+str(props.get('Name'))+' e provisionado/imutavel; AutoConnect nao alterado.'); return
    if not props.get('Favorite'): return
    save_auto(path,props)
    try:
        cm.auto(path,value)
        log('AutoConnect ajustado para '+str(props.get('Name'))+': '+str(value))
    except Exception: log('ConnMan recusou alterar AutoConnect; registro preservado para reversao.')

def active_links():
    _,out=run(['iw','dev'])
    result=[]
    for interface in re.findall(r'^\s*Interface\s+(\S+)',out,re.M):
        _,link=run(['iw','dev',interface,'link'])
        match=re.search(r'^\s*SSID:\s*(.*)$',link,re.M)
        result.append((interface,match.group(1).strip() if match else 'desconectado'))
    return result

def healthy():
    for interface,ssid in active_links():
        if ssid!=HOME_SSID: continue
        rc,ips=run(['ip','-4','-o','addr','show','dev',interface])
        _,routes=run(['ip','-4','route','show','default','dev',interface])
        if rc==0 and ' inet ' in ips and 'default ' in routes: return True
    return False

def diagnose(cm=None):
    version=Path('/usr/share/batocera/batocera.version')
    log('Batocera: '+(version.read_text().strip() if version.exists() else 'nao detectado'))
    values=read_settings(CONF)
    log('wifi.enabled='+values.get('wifi.enabled','ausente')+'; SSID configurado='+values.get('wifi.ssid','ausente'))
    log('ConnMan armazena em '+str(Path('/var/lib/connman').resolve()))
    _,mount=run(['findmnt','-T',str(STORE),'-n','-o','TARGET,FSTYPE'])
    if mount.strip(): log('Montagem ConnMan: '+mount.strip())
    for config in [CONF,Path('/boot/batocera-boot.conf')]:
        settings=read_settings(config)
        for prefix in ['wifi','wifi2','wifi3','wifi.hidden']:
            ssid=settings.get(prefix+'.ssid')
            if ssid: log(config.name+' '+prefix+'.ssid='+ssid+'; credencial local='+str(bool(settings.get(prefix+'.key'))))
    for config in STORE.glob('*.config'):
        cfg=read_ini(config)
        for section in cfg.sections():
            ssid=cfg.get(section,'Name',fallback='')
            if ssid in [HOME_SSID,BLOCK_SSID]: log('Provisionamento '+ssid+' em '+str(config.resolve()))
    for interface,ssid in active_links():
        log('Interface '+interface+'; SSID associado='+ssid)
        for cmd in [['ip','-4','-o','addr','show','dev',interface],['ip','-4','route','show','default','dev',interface]]:
            _,out=run(cmd)
            for line in out.strip().splitlines(): log(line)
    if cm:
        try:
            for path,props in cm.services():
                if props.get('Type')=='wifi' and props.get('Name') in [HOME_SSID,BLOCK_SSID]:
                    log('Perfil '+str(props.get('Name'))+' State='+str(props.get('State'))+' Favorite='+str(bool(props.get('Favorite')))+' AutoConnect='+str(bool(props.get('AutoConnect')))+' Immutable='+str(bool(props.get('Immutable'))))
        except Exception: log('ConnMan ainda indisponivel.')
    rc,code=run(['curl','--silent','--output','/dev/null','--write-out','%{http_code}','--connect-timeout','5','--max-time','12','https://connectivitycheck.gstatic.com/generate_204'])
    log('HTTPS verificado: '+('OK (204)' if rc==0 and code=='204' else 'falhou/portal/data/certificado; codigo='+str(rc)+' HTTP='+code.strip()))

def recover(cm):
    diagnose(cm)
    remove_public_provisioning()
    for attempt in range(1,4):
        if (BASE/'disabled').exists(): log('Ajuste desativado; encerrando recuperacao.'); return False
        log('Tentativa limitada '+str(attempt)+'/3')
        services=list(cm.services())
        for path,props in services:
            if props.get('Type')!='wifi': continue
            if props.get('Name')==BLOCK_SSID:
                set_auto(cm,path,props,False)
                if props.get('State') in ['ready','online','association','configuration']:
                    try: cm.service(path).Disconnect(timeout=10); log('Rede publica Claro desconectada.')
                    except Exception: log('Nao foi possivel desconectar o perfil Claro.')
            elif props.get('Name')==HOME_SSID: set_auto(cm,path,props,True)
        if healthy(): log('Rede residencial com IP e rota; nenhuma reconexao necessaria.'); return True
        # Never interrupt a different network selected by the user.
        if any(ssid not in [HOME_SSID,BLOCK_SSID,'desconectado'] for _,ssid in active_links()):
            log('Outra rede selecionada; sem interferir.'); return False
        home=[(p,v) for p,v in services if v.get('Name')==HOME_SSID and v.get('Type')=='wifi']
        if not home or not any(v.get('Favorite') for _,v in home) or attempt==2:
            provision()
        cm.scan()
        home=[(p,v) for p,v in cm.services() if v.get('Name')==HOME_SSID and v.get('Type')=='wifi']
        for path,props in home[:1]:
            try:
                cm.service(path).Connect(timeout=30)
            except Exception:
                log('Conexao residencial ainda nao concluida. Se pedir agente, configure a senha localmente no menu.')
        for _ in range(6):
            if healthy(): log('Rede residencial com IP e rota confirmados.'); return True
            time.sleep(3)
    log('Limite de tentativas atingido. Sem loop permanente; repetira no proximo boot ou execucao manual.')
    return False

def restore(cm):
    import io
    provisionfile=BASE/'provisioning-original.json'
    if provisionfile.exists():
        for name,sections in json.loads(provisionfile.read_text()).items():
            path=Path(name)
            if not path.is_file(): continue
            cfg=read_ini(path)
            for section,values in sections.items():
                if not cfg.has_section(section): cfg[section]=values
            out=io.StringIO(); cfg.write(out)
            with path.open('w',encoding='utf-8') as f: f.write(out.getvalue())
    file=BASE/'autoconnect-original.json'
    state=json.loads(file.read_text()) if file.exists() else {}
    failed=False
    for path,props in cm.services():
        entry=state.get(str(path))
        if entry and entry['name']==str(props.get('Name')):
            try: cm.auto(path,entry['auto'])
            except Exception: failed=True; log('Falha ao restaurar AutoConnect de '+entry['name'])
    if RUNTIME.is_symlink() and RUNTIME.resolve()==(BASE/'home.config').resolve(): RUNTIME.unlink()
    if failed: return False
    log('AutoConnect anterior restaurado para perfis presentes; backups mantidos.'); return True

def main():
    os.umask(0o077); BASE.mkdir(parents=True,exist_ok=True); os.chmod(BASE,0o700)
    lock=(BASE/'operation.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: print('Ajuste Wi-Fi ja esta em andamento. Aguarde antes de restaurar.'); return 2
    cm=None
    for _ in range(12):
        try: cm=Connman(); cm.services(); break
        except Exception: time.sleep(2)
    if cm is None: log('ConnMan/DBus indisponivel; nenhuma configuracao alterada.'); return 1
    action=sys.argv[1] if len(sys.argv)>1 else 'diagnose'
    if action=='diagnose': diagnose(cm); return 0
    if action=='restore': return 0 if restore(cm) else 1
    ok=recover(cm); diagnose(cm); return 0 if ok else 1

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        # Do not print exception contents: a library might include credentials.
        log('Falha controlada: '+type(exc).__name__+'. Consulte verificar-wifi.sh.'); sys.exit(1)
