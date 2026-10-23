#!/usr/bin/env python3
"""Enable Chromium EME in an idle Aura profile, retaining cookies and settings."""
from pathlib import Path
import hashlib,json,os,shutil,sys

def prepare(profile):
    profile=Path(profile)
    for cmd in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            if ('--user-data-dir='+str(profile)).encode() in cmd.read_bytes().split(b'\0'):
                print('[DRM] Perfil aberto; configuracao adiada. Feche o navegador.');return
        except OSError: pass
    pref=profile/'Default/Preferences'
    data=json.loads(pref.read_text()) if pref.exists() else {}
    web=data.setdefault('webkit',{}).setdefault('webprefs',{})
    if web.get('encrypted_media_enabled') is not True:
        if pref.exists():
            backup=profile.parent/'drm-backups';backup.mkdir(exist_ok=True)
            backup.chmod(0o700)
            saved=backup/('Preferences-'+hashlib.sha256(pref.read_bytes()).hexdigest()[:12]+'.json')
            if not saved.exists(): shutil.copy2(pref,saved);saved.chmod(0o600)
        web['encrypted_media_enabled']=True
        pref.parent.mkdir(parents=True,exist_ok=True)
        temp=pref.with_name('Preferences.aura-drm-new')
        temp.write_text(json.dumps(data,ensure_ascii=False));temp.chmod(0o600);os.replace(temp,pref)
    manifests=list((profile/'WidevineCdm').glob('*/manifest.json'))
    print('[DRM] Conteudo protegido habilitado. Widevine neste perfil:',len(manifests),'versoes encontradas.')
    if not manifests:
        print('[DRM] Se M7701-1003 persistir: PORTS > Aura - Atualizar DRM Netflix; atualizar Widevine e reabrir Netflix.')

if __name__=='__main__':
    prepare(sys.argv[1])
