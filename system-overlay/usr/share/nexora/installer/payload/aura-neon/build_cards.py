#!/usr/bin/env python3
"""Generate lightweight theme cards from Batocera's existing Carbon assets."""
import os,sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
from pathlib import Path
pygame.font.init()
theme=Path(sys.argv[1]);art=theme/'art';out=art/'cards';out.mkdir(exist_ok=True)
fontpath=art/'fonts/Cabin-Regular.ttf'
font=pygame.font.Font(str(fontpath),24) if fontpath.exists() else pygame.font.SysFont('sans',24)
systems=set(p.stem for p in (art/'consoles').glob('*.png'))
systems.update(['ports','apps','flatpak','favorites','all','recent','ps2','psx','snes','mame','xbox'])
try:
 import xml.etree.ElementTree as ET
 for f in [Path('/usr/share/emulationstation/es_systems.cfg'),Path('/userdata/system/configs/emulationstation/es_systems.cfg')]:
  if f.exists():systems.update(e.text for e in ET.parse(f).findall('.//system/theme') if e.text)
except Exception:pass
labels={'ps2':'PLAYSTATION 2','psx':'PLAYSTATION','snes':'SUPER NINTENDO','mame':'ARCADE','ports':'PORTS','apps':'APPS','flatpak':'FLATPAK','favorites':'FAVORITOS','recent':'RECENTES','all':'TODOS OS JOGOS','auto-allgames':'TODOS OS JOGOS','auto-favorites':'FAVORITOS','pcengine':'PC ENGINE','gc':'GAMECUBE'}
for name in sorted(systems):
 if '/' in name or '..' in name:continue
 canvas=pygame.Surface((360,530),pygame.SRCALPHA)
 pygame.draw.rect(canvas,(7,20,34,240),(3,3,354,524),border_radius=26)
 pygame.draw.rect(canvas,(93,135,163,180),(3,3,354,524),2,border_radius=26)
 # The console illustration is native artwork, not a screenshot of a menu.
 source=art/'consoles'/(name+'.png')
 if source.exists() and name not in ('ports','apps','flatpak'):
  loaded=pygame.image.load(str(source));img=pygame.Surface(loaded.get_size(),pygame.SRCALPHA);img.blit(loaded,(0,0));w,h=img.get_size();scale=min(314/w,330/h)
  img=pygame.transform.smoothscale(img,(max(1,int(w*scale)),max(1,int(h*scale))))
  canvas.blit(img,img.get_rect(center=(180,225)))
 else:
  for x in (109,187):
   for y in (152,230):pygame.draw.rect(canvas,(112,164,193),(x,y,64,64),border_radius=8)
 text=labels.get(name,name.replace('_',' ').upper());f=font
 while f.size(text)[0]>316:
  text=text[:-2]+'…'
 rendered=f.render(text,True,(225,242,255));canvas.blit(rendered,rendered.get_rect(center=(180,445)))
 pygame.draw.line(canvas,(63,167,204),(145,486),(215,486),2)
 pygame.image.save(canvas,str(out/(name+'.png')))
print('Theme cards:',len(systems))
