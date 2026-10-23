from pathlib import Path
import hashlib,json,shutil,subprocess,os,time,xml.etree.ElementTree as E
p=Path(__file__).parent;u=Path('/userdata');base=u/'system/aura-neon-runtime'
mark=base/'v82.done'
if mark.exists():raise SystemExit(0)
for rel,h in json.loads((p/'manifest.json').read_text()).items():
 assert hashlib.sha256((p/rel).read_bytes()).hexdigest()==h,rel
binary=base/'bin/emulationstation';old='44a6d8dec8aaec7aa986ec5986d1be4e8a63d62f504ea4bf1530fc49171a1d5f'
new=hashlib.sha256((p/'emulationstation').read_bytes()).hexdigest()
assert binary.exists() and hashlib.sha256(binary.read_bytes()).hexdigest() in (old,new),'Versao da interface diferente; atualizacao cancelada.'
stage=binary.with_suffix('.v82-stage');shutil.copy2(p/'emulationstation',stage);stage.chmod(0o755)
subprocess.run([str(stage),'--help'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'LD_BIND_NOW':'1'})
theme=u/'themes/aura-7-native';store=u/'system/aura-store-native'
back=base/('backup-v82-'+str(time.time_ns()));back.mkdir(parents=True)
targets=[binary,base/'binary.sha256',theme/'theme.xml',store/'neon.py',store/'install.py',store/'assets/aura-store-logo.png']
targets += [u/f'roms/{system}/gamelist.xml' for system in ('apps','ports')]
targets += [u/f'roms/{system}/images/batocera-store-aura.png' for system in ('apps','ports')]
for path in targets:
 if path.exists():
  target=back/path.relative_to(u);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
try:
 shutil.copytree(p/'menu82',theme/'art/menu82',dirs_exist_ok=True)
 shutil.copy2(p/'theme.xml',theme/'theme.xml')
 shutil.copy2(p/'neon.py',store/'neon.py')
 shutil.copy2(p/'aura-store-logo.png',store/'assets/aura-store-logo.png')
 for system in ('apps','ports'):
  images=u/f'roms/{system}/images';images.mkdir(parents=True,exist_ok=True)
  shutil.copy2(p/'aura-store-logo.png',images/'batocera-store-aura.png')
  gl=images.parent/'gamelist.xml'
  if not gl.exists():continue
  t=E.parse(gl)
  for game in t.getroot().findall('game'):
   if Path(game.findtext('path') or '').name.casefold() not in ('batocera store.app','batocera store.sh'):continue
   for field in ('image','thumbnail','marquee'):
    e=game.find(field)
    if e is None:e=E.SubElement(game,field)
    e.text='./images/batocera-store-aura.png'
  t.write(gl,encoding='UTF-8',xml_declaration=True)
 installer=store/'install.py'
 text=installer.read_text()
 text=text.replace("'image':'./images/batocera-store-aura.svg','thumbnail':'./images/batocera-store-aura.svg'","'image':'./images/batocera-store-aura.png','thumbnail':'./images/batocera-store-aura.png'")
 installer.write_text(text)
 os.replace(stage,binary)
 (base/'binary.sha256').write_text(new+'  bin/emulationstation\n')
 mark.write_text(new+'\n')
except Exception:
 for saved in back.rglob('*'):
  if saved.is_file():
   target=u/saved.relative_to(back);tmp=target.with_suffix(target.suffix+'.restore');shutil.copy2(saved,tmp);os.replace(tmp,target)
 raise
print('AURA 8.2 instalada. Reinicie pelo menu. Backup:',back)
