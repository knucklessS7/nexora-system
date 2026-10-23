from pathlib import Path
import shutil
import xml.etree.ElementTree as E
p=Path('/userdata/themes/aura-7-native/theme.xml')
if p.exists():
 tree=E.parse(p);changed=False
 for node in tree.getroot().iter('controllerActivity'):
  visible=node.find('visible')
  if visible is None:visible=E.SubElement(node,'visible')
  if visible.text!='false':visible.text='false';changed=True
 if changed:
  backup=p.with_name('theme.before-hide-controller.xml')
  if not backup.exists():shutil.copy2(p,backup)
  tmp=p.with_suffix('.hide-new');tree.write(tmp,encoding='utf-8',xml_declaration=True);tmp.replace(p)
  print('Indicador de controle oculto; tema preservado.')
