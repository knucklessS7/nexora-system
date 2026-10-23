from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
P=Path(__file__).parent;B=Path('/userdata/system/aura-store-native');N=Path('/userdata/system/aura-neon-runtime')
def apply():
    if Path('/boot/AURA-NEON-DESATIVAR').exists() or (N/'recovery-disabled').exists():
        print('Recuperação ativa; atualização de remoção ignorada.');return
    manifest=json.loads((P/'manifest.json').read_text())
    for name,h in manifest.items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
    marker=N/'remove-fix.done';revision=hashlib.sha256((P/'manifest.json').read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text()!=revision:
        binary=N/'bin/emulationstation';new=manifest['emulationstation']
        assert hashlib.sha256(binary.read_bytes()).hexdigest() in ('4db12f3a7d6cb6e44875c39f64eecbed79cb19e3cc030ea51f729178b58b3083','72a0faf8f315a8a79a0cf6a7564c5c3ae12c0859e5cf57a8defe55a133443108','9f17575214bba2866582f5432ac462244d9b00544eb2758faac36d1284a7d898',new),'Interface diferente; nada alterado.'
        candidate=binary.with_suffix('.remove-new');shutil.copy2(P/'emulationstation',candidate);candidate.chmod(0o755)
        subprocess.run([str(candidate),'--help'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'LD_BIND_NOW':'1'})
        reconcile=B/'reconcile.py';text=reconcile.read_text(encoding='utf-8')
        needle="            if appid=='org.chromium.Chromium' and appid not in rows and 'com.google.Chrome' in canonical:"
        patch="            if appid and appid not in rows:\n                changes.archive(path);removed_apps.add(path.name);continue\n"
        if patch not in text:
            assert needle in text,'Versão diferente do organizador.';text=text.replace(needle,patch+needle)
        compile(text,str(reconcile),'exec')
        backup=N/('backup-remove-'+str(time.time_ns()));backup.mkdir()
        targets=[binary,N/'binary.sha256',reconcile,B/'remove_app.py'];saved={}
        for i,t in enumerate(targets):
            if t.exists():shutil.copy2(t,backup/str(i));saved[t]=backup/str(i)
        (backup/'targets.json').write_text(json.dumps({str(k):str(v) for k,v in saved.items()},indent=2))
        try:
            shutil.copy2(P/'remove_app.py',B/'remove_app.py')
            tmp=reconcile.with_suffix('.remove-new');tmp.write_text(text,encoding='utf-8');os.replace(tmp,reconcile)
            os.replace(candidate,binary);(N/'binary.sha256').write_text(new+'  bin/emulationstation\n')
            marker.write_text(revision)
            if (N/'disabled-after-failure').exists():
                (N/'enabled').touch()
        except Exception:
            for target,source in saved.items():
                tmp=target.with_suffix('.restore');shutil.copy2(source,tmp);os.replace(tmp,target)
            raise
    import xml.etree.ElementTree as ET
    ports=Path('/userdata/roms/ports');maintenance=Path('/userdata/system/aura/maintenance');maintenance.mkdir(parents=True,exist_ok=True)
    names={'Aura - Reparar streaming.sh','Aura - Corrigir streaming.sh','Aura - Corrigir streamings.sh','Aura - Atualizar DRM Netflix.sh','Aura - Conteudo protegido Netflix.sh','Aura - Instalar agora.sh'}
    gl=ports/'gamelist.xml';tree=ET.parse(gl) if gl.exists() else None
    for name in names:
        old=ports/name
        if old.is_file() and not old.is_symlink():
            dest=maintenance/name
            if dest.exists() and dest.read_bytes()!=old.read_bytes():dest=maintenance/(name+'.'+str(time.time_ns())+'.backup')
            shutil.move(str(old),str(dest))
    if tree is not None:
        for item in list(tree.getroot().findall('game')):
            if (item.findtext('path') or '').removeprefix('./') in names:tree.getroot().remove(item)
        temp=gl.with_suffix('.maintenance-new');tree.write(temp,encoding='utf-8',xml_declaration=True);os.replace(temp,gl)
    # User explicitly requested removal of Telegram. Apply once, only after success.
    done=B/'telegram-removal.done'
    if not done.exists():
        subprocess.run(['python3',str(B/'remove_app.py'),'--appid','org.telegram.desktop'],check=True)
        done.write_text('Aplicativo e atalhos removidos.\n')
    report=B/'last-removal.json'
    if report.exists():
        readonly=bool(os.statvfs('/boot').f_flag&os.ST_RDONLY)
        try:
            if readonly:subprocess.run(['mount','-o','remount,rw','/boot'],check=True)
            shutil.copy2(report,'/boot/AURA-REMOCAO.json')
        finally:
            if readonly:subprocess.run(['mount','-o','remount,ro','/boot'],check=True)
    print('Remoção AURA preparada; reinicie para carregar o executável.')
if __name__=='__main__':apply()
