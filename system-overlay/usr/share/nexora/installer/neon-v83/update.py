from pathlib import Path
import hashlib, json, os, shutil, time, subprocess

def install(userdata=Path('/userdata')):
    p=Path(__file__).parent;base=userdata/'system/aura-neon-runtime'
    marker=base/'v83.done'
    manifest=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
    revision=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest()
    if marker.exists() and marker.read_text().strip()==revision:return
    for rel,digest in manifest.items():
        if hashlib.sha256((p/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Arquivo inválido: '+rel)
    store=userdata/'system/aura-store-native';theme=userdata/'themes/aura-7-native'
    if not (base/'v82.done').exists():raise RuntimeError('Instale AURA 8.2 antes desta atualização.')
    binary=base/'bin/emulationstation'
    newhash=hashlib.sha256((p/'emulationstation').read_bytes()).hexdigest()
    oldhash=hashlib.sha256(binary.read_bytes()).hexdigest()
    if oldhash not in ('8977463dffd9065463d6aa32b3e8f3a6a71b086daffd71fb9f03a1540d877c14',newhash):raise RuntimeError('Binário AURA diferente; atualização cancelada.')
    candidate=binary.with_name('emulationstation.v83-check');shutil.copy2(p/'emulationstation',candidate);candidate.chmod(0o755)
    subprocess.run([str(candidate),'--help'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'LD_BIND_NOW':'1'})
    candidate.unlink()
    main=store/'main.py';text=main.read_text(encoding='utf-8')
    old='Nenhum atalho local encontrado. Não será baixado automaticamente.'
    new='Instalação automática pelo repositório oficial do RGSX.'
    if old not in text and new not in text:raise RuntimeError('Versão desconhecida da loja; arquivos preservados.')
    text=text.replace(old,new).replace("action='A · ABRIR' if a['_installed'] else 'NÃO INSTALADO'\n            enabled=a['_installed']", "action='A · ABRIR' if a['_installed'] else 'A · INSTALAR'\n            enabled=True")
    compile(text,str(main),'exec')
    for name in ('neon.py','rgsx_install.py'):compile((p/name).read_text(encoding='utf-8'),name,'exec')
    mapping={p/'theme.xml':theme/'theme.xml',p/'neon.py':store/'neon.py',p/'rgsx_install.py':store/'rgsx_install.py'}
    mapping.update({s:theme/'art/menu83'/s.name for s in (p/'menu83').iterdir()})
    backup=base/('backup-v83-'+str(time.time_ns()));backup.mkdir(parents=True)
    targets=[*mapping.values(),main,binary,base/'binary.sha256'];existing=set()
    for dst in targets:
        if dst.exists():
            saved=backup/dst.relative_to(userdata);saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,saved);existing.add(dst)
    changed=[]
    try:
        for src,dst in mapping.items():
            dst.parent.mkdir(parents=True,exist_ok=True)
            temp=dst.with_name(dst.name+'.v83-new');shutil.copy2(src,temp);os.replace(temp,dst);changed.append(dst)
        temp=main.with_suffix('.v83-new');temp.write_text(text,encoding='utf-8');os.replace(temp,main);changed.append(main)
        temp=binary.with_suffix('.v83-new');shutil.copy2(p/'emulationstation',temp);temp.chmod(0o755);os.replace(temp,binary);changed.append(binary)
        (base/'binary.sha256').write_text(newhash+'  bin/emulationstation\n');changed.append(base/'binary.sha256')
        marker.write_text(revision+'\n')
    except Exception:
        for dst in reversed(changed):
            if dst in existing:shutil.copy2(backup/dst.relative_to(userdata),dst)
            else:dst.unlink(missing_ok=True)
        raise
    print('AURA 8.3: menus e instalador RGSX atualizados. Backup:',backup)

if __name__=='__main__':install()
