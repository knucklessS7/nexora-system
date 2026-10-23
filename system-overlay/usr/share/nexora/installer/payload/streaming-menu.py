#!/usr/bin/env python3
"""Original Aura menu inspired by RGSX's grid and confirm/back conventions."""
import importlib.util,os,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
os.environ.setdefault('DISPLAY',':0')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
BASE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('bridge',BASE/'controller-bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
APPS=[('prime','Prime Video'),('netflix','Netflix'),('disney','Disney+'),('globoplay','Globoplay'),('youtube','YouTube'),('spotify','Spotify'),('apple_music','Apple Music'),('deezer','Deezer'),('youtube_music','YouTube Music')]

def main():
    pygame.display.init();pygame.font.init();pygame.joystick.init()
    configs=[]
    for path in ['/userdata/system/configs/emulationstation/es_input.cfg','/usr/share/emulationstation/es_input.cfg']:
        try:configs.extend(ET.parse(path).getroot().findall('inputConfig'))
        except (OSError,ET.ParseError):pass
    devices={}
    def add(index):
        joy=pygame.joystick.Joystick(index);joy.init()
        bindings=bridge.mapping(configs,joy.get_guid(),joy.get_name())
        try:
            from pygame._sdl2 import controller
            controller.init()
            if controller.is_controller(index):
                pad=controller.Controller(index)
                for name,value in pad.get_mapping().items():
                    if name in ('a','b','start','back') and value.startswith('b') and value[1:].isdigit():
                        bindings['select' if name=='back' else name]=('button',int(value[1:]),1)
                pad.quit()
        except (ImportError,pygame.error,AttributeError):pass
        devices[joy.get_instance_id()]=(joy,bindings,bridge.Repeater())
    def screen():
        pygame.display.init()
        return pygame.display.set_mode((0,0),pygame.FULLSCREEN)
    surface=screen();selected=0;clock=pygame.time.Clock();running=True
    for index in range(pygame.joystick.get_count()):add(index)
    while running:
        keys=[]
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False
            elif event.type==pygame.JOYDEVICEADDED:add(event.device_index)
            elif event.type==pygame.JOYDEVICEREMOVED:devices.pop(event.instance_id,None)
            elif event.type==pygame.KEYDOWN:
                keys.append({pygame.K_UP:'Up',pygame.K_DOWN:'Down',pygame.K_LEFT:'Left',pygame.K_RIGHT:'Right',pygame.K_RETURN:'Return',pygame.K_ESCAPE:'Escape'}.get(event.key,''))
        for joy,bindings,repeat in devices.values():
            try:
                key=bridge.action(joy,bindings)
                if repeat.step(key,time.monotonic()):keys.append(key)
            except pygame.error:pass
        for key in keys:
            if key in ('Escape','alt+F4'):running=False
            elif key in ('Up','Down','Left','Right'):
                selected=(selected+{'Up':-3,'Down':3,'Left':-1,'Right':1}[key])%len(APPS)
            elif key=='Return':
                pygame.display.quit()
                subprocess.run(['bash',str(BASE/'streaming-launch.sh'),APPS[selected][0]],check=False)
                surface=screen()
                pygame.event.clear()
        width,height=surface.get_size();surface.fill((9,16,29))
        font=pygame.font.Font(None,max(25,int(height*.038)))
        title=pygame.font.Font(None,max(36,int(height*.065)))
        surface.blit(title.render('AURA  |  STREAMINGS',True,(240,247,255)),(int(width*.07),int(height*.07)))
        subtitle='Setas / direcional: escolher     A / Enter: abrir     B / Esc: sair'
        surface.blit(font.render(subtitle,True,(146,171,201)),(int(width*.07),int(height*.16)))
        for i,(_,name) in enumerate(APPS):
            box=pygame.Rect(int(width*(.07+(i%3)*.295)),int(height*(.25+(i//3)*.18)),int(width*.27),int(height*.145))
            pygame.draw.rect(surface,(24,48,70) if i==selected else (20,29,45),box,border_radius=14)
            if i==selected:pygame.draw.rect(surface,(71,214,237),box,4,border_radius=14)
            label=font.render(name,True,(245,245,245));surface.blit(label,label.get_rect(center=box.center))
        tip='No site: F1 ajuda | Xbox Y: ponteiro | Select + Start: voltar ao menu'
        surface.blit(font.render(tip,True,(146,171,201)),(int(width*.07),int(height*.85)))
        pygame.display.flip();clock.tick(30)
    pygame.quit()

if __name__=='__main__':main()
