from pathlib import Path
import fcntl,hashlib,json,os,shutil,subprocess,time

def clean_stale(ports,now=None):
    now=time.time() if now is None else now
    removed=[]
    root=ports.resolve()
    for directory in ports.glob('.aura-rgsx-*'):
        if directory.is_symlink() or not directory.is_dir() or directory.resolve().parent!=root:continue
        if now-directory.stat().st_mtime<86400:continue
        entries=list(directory.iterdir())
        if not entries or any(e.name not in ('release.zip','stage') for e in entries):continue
        paths=list(directory.rglob('*'))
        if any(e.is_symlink() for e in paths):continue
        size=sum(e.stat().st_size for e in paths if e.is_file())
        shutil.rmtree(directory)
        removed.append({'directory':str(directory),'bytes':size})
    return removed

def main():
    here=Path(__file__).parent;base=Path('/userdata/system/aura-store-native')
    ports=Path('/userdata/roms/ports')
    if not base.is_dir() or not ports.is_dir():raise RuntimeError('Loja ou SHARE ausente.')
    with (base/'rgsx-install.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=shutil.disk_usage(ports).free
        removed=clean_stale(ports)
        source=here/'rgsx_install.py';target=base/source.name
        expected=json.loads((here/'manifest.json').read_text())[source.name]
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise RuntimeError('Atualização corrompida.')
        compile(source.read_text(encoding='utf-8'),str(source),'exec')
        if not target.exists() or target.read_bytes()!=source.read_bytes():
            backup=base/'rgsx_install.before-space-fix.py'
            if target.exists() and not backup.exists():shutil.copy2(target,backup)
            temp=target.with_suffix('.space-new');shutil.copy2(source,temp);os.replace(temp,target)
        report={'free_before_bytes':before,'free_after_bytes':shutil.disk_usage(ports).free,'removed_installer_temporaries':removed,'needed_share_mib':166,'local_package':Path('/boot/aura-installer/rgsx-cache/RGSX-linux.zip').exists(),'note':'Nenhum jogo, save, perfil, Flatpak ou configuração removido.'}
        output=base/'space-report.json';output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    readonly=bool(os.statvfs('/boot').f_flag&os.ST_RDONLY)
    try:
        if readonly:subprocess.run(['mount','-o','remount,rw','/boot'],check=True)
        shutil.copy2(output,'/boot/AURA-ESPACO-RGSX.json')
    finally:
        if readonly:subprocess.run(['mount','-o','remount,ro','/boot'],check=True)
    print(json.dumps(report))

if __name__=='__main__':main()
