from pathlib import Path
import hashlib,json,shutil,sys,time,os,subprocess,xml.etree.ElementTree as E
p=Path(sys.argv[1]); u=Path('/userdata'); base=u/'system/aura-neon-runtime'
for rel,h in json.loads((p/'manifest.json').read_text()).items():
 assert hashlib.sha256((p/rel).read_bytes()).hexdigest()==h,rel
binary=base/'bin/emulationstation';binary.parent.mkdir(parents=True,exist_ok=True)
stage=base/'bin/emulationstation.stage';shutil.copy2(p/'emulationstation',stage);stage.chmod(0o755)
subprocess.run([str(stage),'--help'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'LD_BIND_NOW':'1'})
conf=u/'system/configs/emulationstation/es_settings.cfg'
tree=E.parse(conf) if conf.exists() else E.ElementTree(E.Element('config'))
app=u/'roms/apps/Batocera Store.app'; gl=u/'roms/apps/gamelist.xml'
gt=E.parse(gl) if gl.exists() else E.ElementTree(E.Element('gameList'))
back=base/('backup-'+str(time.time_ns()));back.mkdir()
for path in (conf,app,gl,u/'themes/aura-7-native',u/'system/aura-store-native',u/'system/batocera.conf',binary,u/'system/services/aura_neon'):
 if path.exists():
  target=back/path.relative_to(u);target.parent.mkdir(parents=True,exist_ok=True)
  if path.is_dir():shutil.copytree(path,target)
  else:shutil.copy2(path,target)
theme=u/'themes/aura-7-native'
if theme.exists():theme.rename(theme.with_name('aura-7-native-before-v81-'+str(time.time_ns())))
shutil.copytree(p/'theme',theme)
store=u/'system/aura-store-native';shutil.copytree(p/'store',store,dirs_exist_ok=True)
os.replace(stage,binary)
(base/'binary.sha256').write_text(hashlib.sha256(binary.read_bytes()).hexdigest()+'  bin/emulationstation\n')
(base/'dispatch').mkdir(exist_ok=True)
shutil.copy2(p/'dispatcher',base/'dispatch/emulationstation');(base/'dispatch/emulationstation').chmod(0o755)
services=u/'system/services';services.mkdir(parents=True,exist_ok=True)
shutil.copy2(p/'service',services/'aura_neon');(services/'aura_neon').chmod(0o755)
subprocess.run(['python3',str(store/'install.py')],check=True)
app.parent.mkdir(parents=True,exist_ok=True)
app.write_text('managed=aura-neon-v81\nname=Batocera Store\ntype=command\nexec=bash /userdata/system/aura-store-native/launch.sh\n')
gr=gt.getroot();game=None
for item in list(gr.findall('game')):
 if (item.findtext('path') or '').removeprefix('./')==app.name:
  if game is None:game=item
  else:gr.remove(item)
if game is None:game=E.SubElement(gr,'game')
for k,v in {'path':'./'+app.name,'name':'Batocera Store','desc':'AURA Neon 8.1 - aplicativos e streaming','image':'/userdata/roms/ports/images/batocera-store-aura.svg'}.items():
 e=game.find(k)
 if e is None:e=E.SubElement(game,k)
 e.text=v
gt.write(gl,encoding='UTF-8',xml_declaration=True)
root=tree.getroot()
for typ,key,val in [('string','ThemeSet','aura-7-native'),('bool','ShowClock','true')]:
 e=next((x for x in root.findall(typ) if x.get('name')==key),None)
 if e is None:e=E.SubElement(root,typ,{'name':key})
 e.set('value',val)
conf.parent.mkdir(parents=True,exist_ok=True);tree.write(conf,encoding='UTF-8',xml_declaration=True)
state=u/'system/aura/state';state.mkdir(parents=True,exist_ok=True);(state/'neon-v80.done').touch()
print('Arquivos e imagens verificados. Backup:',back)
