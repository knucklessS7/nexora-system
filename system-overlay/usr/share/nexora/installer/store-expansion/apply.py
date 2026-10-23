from pathlib import Path
import hashlib,json,os,re,shlex,shutil,subprocess,time
P=Path(__file__).parent
def main_patch(s):
    if '# AURA explicit web install v1' in s:return s
    s=s.replace("info='Use teclado/mouse. Alt+F4 para sair.' if a['_installed'] else 'Aguarde a configuração do Aura ou reinicie.'", "info='Use controle ou teclado. Alt+F4 para sair.' if a['_installed'] else 'Adiciona o serviço a APPS e à segunda fileira. Pode exigir assinatura.'")
    s=s.replace("action='A · ABRIR' if a['_installed'] else 'AGUARDANDO CONFIGURAÇÃO'\n            enabled=a['_installed']", "action='A · ABRIR' if a['_installed'] else 'A · INSTALAR'\n            enabled=True")
    old="""            if not script.is_file():
                self.notify('Aguarde a configuração ou use Aura - Reparar streaming em PORTS.',8)
                return"""
    new="""            if not script.is_file():
                # AURA explicit web install v1
                try:
                    from web_apps import install
                    install(a['id']);self.refresh()
                    self.notify('Instalado. Use Abrir ou volte ao menu para ver o aplicativo.',6)
                except Exception as e:self.notify('Não foi possível instalar: '+str(e),10)
                return"""
    assert old in s,'Loja diferente: bloco de instalação não encontrado.';s=s.replace(old,new)
    s=s.replace('Instalação concluída. Atualize a lista de jogos para ver o atalho.','Instalação concluída. Ao sair da loja, APPS e a segunda fileira serão atualizados.')
    compile(s,'main.py','exec');return s
def removal_patch(s):
    if 'def record_deleted(' in s:return s
    anchor='def remove(appid,selected=None):'
    helper="""def record_deleted(selected):
    if selected is None:return
    p=BASE/'removed-shortcuts.json'
    rows=json.loads(p.read_text()) if p.exists() else []
    if str(selected) not in rows:rows.append(str(selected))
    tmp=p.with_suffix('.new');tmp.write_text(json.dumps(rows));os.replace(tmp,p)

"""
    assert anchor in s;s=s.replace(anchor,helper+anchor)
    # Both branches run under the existing reconcile lock.
    s=s.replace('                selected.unlink()', '                record_deleted(selected)\n                selected.unlink()')
    compile(s,'remove_app.py','exec');return s
def install(u=Path('/userdata')):
    base=u/'system/aura-store-native';runtime=u/'system/aura/streaming-native-v4'
    manifest=json.loads((P/'manifest.json').read_text())
    for rel,digest in manifest.items():assert hashlib.sha256((P/rel).read_bytes()).hexdigest()==digest,rel
    revision=hashlib.sha256((P/'manifest.json').read_bytes()).hexdigest();marker=base/'expansion.done'
    if marker.exists() and marker.read_text()==revision:return
    changes={base/'main.py':main_patch((base/'main.py').read_text(encoding='utf-8')).encode(),base/'remove_app.py':removal_patch((base/'remove_app.py').read_text(encoding='utf-8')).encode()}
    neon=(base/'neon.py').read_text(encoding='utf-8').replace("'Configurar' if a['kind']=='aura_app'", "'Instalar' if a['kind']=='aura_app'")
    if '            self.rgsx_rect=pygame.Rect(318,755,1228,82)' in neon:
        start=neon.index('            self.rgsx_rect=pygame.Rect(318,755,1228,82)')
        end=neon.index("        elif self.filter=='Meu PC':",start)
        neon=neon[:start]+neon[end:]
    neon='\n'.join(line for line in neon.split('\n') if "elif self.filter=='Home' and getattr(self,'rgsx_rect'" not in line)
    neon=neon.replace('img=pygame.transform.smoothscale(self.icon_cache[key],(size,size));self.screen.blit(img,(x,y));return', 'source=self.icon_cache[key];w,h=source.get_size();scale=min(size/w,size/h,1.0);dims=(max(1,round(w*scale)),max(1,round(h*scale)));img=pygame.transform.smoothscale(source,dims);self.screen.blit(img,(x+(size-dims[0])//2,y+(size-dims[1])//2));return')
    compile(neon,'neon.py','exec')
    changes[base/'neon.py']=neon.encode()
    reconcile=base/'reconcile.py';s=reconcile.read_text(encoding='utf-8')
    anchor='def reconcile(rows=None):'
    if '# AURA removed shortcut priority' not in s:
        assert anchor in s
        s=s.replace(anchor,anchor+'\n    # AURA removed shortcut priority\n    from web_apps import enforce_removed\n    enforce_removed()',1)
    changes[reconcile]=s.encode()
    for rel in manifest:
        if rel.startswith('assets/') or rel in ('catalog.json','web_apps.py','sources.json','art-sources.json'):changes[base/rel]=(P/rel).read_bytes()
    apps=json.loads((P/'catalog.json').read_text(encoding='utf-8'))['apps']
    launcher=runtime/'launch.sh'
    if launcher.exists():
        s=launcher.read_text(encoding='utf-8');anchor='  *) echo "Aplicativo desconhecido: $ID"; exit 2 ;;'
        assert anchor in s,'Launcher diferente: catálogo não aplicado.'
        if True:
            rows=[]
            for a in apps:
                if a['kind']!='aura_app':continue
                ident=a['runtime_id'];assert re.fullmatch('[a-z0-9_]+',ident)
                if not re.search(r'^\s*'+re.escape(ident)+r'\)',s,re.M):rows.append('  '+ident+') URL='+shlex.quote(a['url'])+' ;;')
            if rows:s=s.replace(anchor,'  # AURA expanded catalog v1\n'+'\n'.join(rows)+'\n'+anchor)
        changes[launcher]=s.encode()
        rt=runtime/'runtime.py';s=rt.read_text(encoding='utf-8')
        if '# AURA catalog runtime ids' not in s:
            anchor='    if app not in APPS:';assert anchor in s
            ids=[a['runtime_id'] for a in apps if a['kind']=='aura_app']
            s=s.replace(anchor,'    # AURA catalog runtime ids\n    if app not in APPS and app not in '+repr(tuple(ids))+':')
        else:
            ids=[a['runtime_id'] for a in apps if a['kind']=='aura_app']
            s=re.sub(r'^    if app not in APPS and app not in .*:$','    if app not in APPS and app not in '+repr(tuple(ids))+':',s,flags=re.M)
        compile(s,'runtime.py','exec');changes[rt]=s.encode()
    else:print('AVISO: runtime de streaming não está presente neste sistema; atalhos podem ser instalados, mas não abertos.')
    backup=base/('backup-expansion-'+str(time.time_ns()));backup.mkdir(parents=True)
    for i,(dst,data) in enumerate(changes.items()):
        if dst.exists():shutil.copy2(dst,backup/str(i))
    (backup/'targets.json').write_text(json.dumps({str(i):str(p) for i,p in enumerate(changes)},indent=2))
    for dst,data in changes.items():
        dst.parent.mkdir(parents=True,exist_ok=True);temp=dst.with_name(dst.name+'.expansion-new');temp.write_bytes(data)
        if dst.exists():temp.chmod(dst.stat().st_mode&0o777)
        os.replace(temp,dst)
    # Update images only for installed web shortcuts; never recreate removed apps.
    import xml.etree.ElementTree as ET
    gl=u/'roms/apps/gamelist.xml'
    if gl.exists():
        tree=ET.parse(gl)
        for a in apps:
            if a['kind']!='aura_app' or not (u/'roms/apps'/a['shortcut']).is_file():continue
            icon=base/'assets/icons'/(a['id']+'.png');dest=u/'roms/apps/images'/('aura-'+a['id']+'.png')
            if not icon.exists():continue
            dest.parent.mkdir(exist_ok=True);shutil.copy2(icon,dest)
            for game in tree.getroot().findall('game'):
                if (game.findtext('path') or '').removeprefix('./')!=a['shortcut']:continue
                for key in ('image','thumbnail','marquee'):
                    node=game.find(key)
                    if node is None:node=ET.SubElement(game,key)
                    node.text=str(dest)
        shutil.copy2(gl,backup/'apps-gamelist.xml')
        temp=gl.with_suffix('.art-new');tree.write(temp,encoding='utf-8',xml_declaration=True);os.replace(temp,gl)
    marker.write_text(revision)
    print('Catálogo atualizado:',len(apps),'entradas. Nenhum aplicativo instalado automaticamente.')
if __name__=='__main__':install()
