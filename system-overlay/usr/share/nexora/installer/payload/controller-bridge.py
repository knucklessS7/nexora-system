#!/usr/bin/env python3
"""Translate the saved Batocera controller mapping into X11 browser keys."""
import os
import json
import sys
import time
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def mapping(configs, guid, name):
    matches = [c for c in configs if c.get('deviceGUID', '').lower() == guid.lower()]
    if not matches:
        matches = [c for c in configs if c.get('deviceName') == name]
    if not matches:
        return {}
    return {e.get('name'): (e.get('type'), int(e.get('id')), int(e.get('value', '1')))
            for e in matches[0].findall('input')}


def sdl_binding(value, dest):
    if value.startswith('b') and value[1:].isdigit():
        return ('button', int(value[1:]), 1)
    if value.startswith('h'):
        parts=value[1:].split('.')
        if len(parts)==2 and all(x.isdigit() for x in parts):
            return ('hat', int(parts[0]), int(parts[1]))
    invert=-1 if value.endswith('~') else 1
    value=value.rstrip('~')
    sign=-1 if value.startswith('-') else 1
    axis=value.lstrip('+-')
    if axis.startswith('a') and axis[1:].isdigit():
        if dest in ('joystick1left','joystick1up'): sign=-1
        return ('axis',int(axis[1:]),sign*invert)
    return None


def pressed(joy, spec):
    if spec is None:
        return False
    kind, index, value = spec
    try:
        if kind == 'button':
            return bool(joy.get_button(index))
        if kind == 'axis':
            return joy.get_axis(index) * value > .65
        if kind == 'hat':
            x, y = joy.get_hat(index)
            bits = (1 if y > 0 else 4 if y < 0 else 0) | (2 if x > 0 else 8 if x < 0 else 0)
            return (bits & value) == value and value != 0
    except (IndexError, RuntimeError):
        pass
    return False


def action(joy, bindings):
    def down(name):
        return pressed(joy, bindings.get(name))
    if down('start') and down('select'):
        return 'alt+F4'
    if down('y'):
        return 'F2'
    if down('x'):
        return 'space'
    if down('b'):
        return 'Escape'
    if down('a'):
        return 'Return'
    for direction, key in [('up', 'Up'), ('down', 'Down'), ('left', 'Left'), ('right', 'Right')]:
        if down(direction):
            return key
    for name, negative, positive in [('joystick1left', 'Left', 'Right'), ('joystick1up', 'Up', 'Down')]:
        spec = bindings.get(name)
        if spec and spec[0] == 'axis':
            if pressed(joy, spec):
                return negative
            if pressed(joy, (spec[0], spec[1], -spec[2])):
                return positive
    return ''


class Repeater:
    def __init__(self):
        self.last = ''
        self.next = 0

    def step(self, key, now):
        fresh = key != self.last
        fire = bool(key) and (fresh or (key in ('Up', 'Down', 'Left', 'Right') and now >= self.next))
        if fire:
            self.next = now + (.38 if fresh else .17)
        self.last = key
        return fire


def browser_focused():
    try:
        window = subprocess.check_output(['xdotool', 'getactivewindow'], stderr=subprocess.DEVNULL, timeout=1).strip()
        windows = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--class', 'chromium|[Cc]hrome'], stderr=subprocess.DEVNULL, timeout=1).split()
        return window in windows
    except (OSError, subprocess.SubprocessError):
        return False


CALIBRATION_FILE=Path('/userdata/system/aura/controller-buttons.json')
CALIBRATION_STATUS=Path('/tmp/aura-controller-calibration.json')

class ButtonCalibration:
    names=('a','b','x','y')
    labels=('A (verde, embaixo)','B (vermelho, direita)','X (azul, esquerda)','Y (amarelo, em cima)')
    def __init__(self, identity, bindings):
        self.identity=identity;self.bindings=bindings;self.stage=0;self.armed=False
        self.captured={};self.finished=False;self.started=False
        try:
            saved=json.loads(CALIBRATION_FILE.read_text()).get(identity,{})
            if set(saved)==set(self.names) and all(type(v)==int and 0<=v<256 for v in saved.values()) and len(set(saved.values()))==4:
                bindings.update({k:('button',v,1) for k,v in saved.items()});self.finished=True
        except (OSError,ValueError,TypeError,AttributeError):pass
    def status(self,message):
        temp=CALIBRATION_STATUS.with_suffix('.tmp')
        temp.write_text(json.dumps({'message':message,'time':time.time()}));os.replace(temp,CALIBRATION_STATUS)
    def step(self,buttons):
        if self.finished:return False
        if not self.started:
            self.started=True;self.status('Configurar controle: solte os botoes e aperte '+self.labels[0])
        if self.stage==4:
            if not buttons:
                self.finished=True;self.status('Controle salvo. A abre, B volta, X pausa, Y alterna ponteiro.')
            return True
        if not buttons:self.armed=True;return True
        if not self.armed or len(buttons)!=1:return True
        self.armed=False;button=buttons[0]
        if button in self.captured.values():
            self.status('Este botao ja foi registrado. Solte e aperte '+self.labels[self.stage]);return True
        self.captured[self.names[self.stage]]=button;self.stage+=1
        if self.stage<4:
            self.status('Registrado. Solte os botoes e aperte '+self.labels[self.stage]);return True
        try:
            try:db=json.loads(CALIBRATION_FILE.read_text())
            except (OSError,ValueError):db={}
            if not isinstance(db,dict):db={}
            db[self.identity]=self.captured
            CALIBRATION_FILE.parent.mkdir(parents=True,exist_ok=True)
            temp=CALIBRATION_FILE.with_suffix('.tmp');temp.write_text(json.dumps(db));os.replace(temp,CALIBRATION_FILE)
            self.bindings.update({k:('button',v,1) for k,v in self.captured.items()})
            self.status('Solte os botoes para concluir.')
        except OSError:
            self.stage=0;self.captured={};self.status('Nao foi possivel salvar. Solte e aperte '+self.labels[0])
        return True


def main():
    ready = Path(sys.argv[1])
    if not shutil.which('xdotool'):
        raise RuntimeError('xdotool ausente; usando controle da extensao')
    os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'
    os.environ['SDL_VIDEODRIVER'] = 'x11'  # Batocera build has no dummy video driver
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    import pygame
    # The event queue requires SDL video initialization, even without a window.
    # Otherwise event.get() raises "video system not initialized" after READY.
    pygame.display.init()
    pygame.joystick.init()
    pygame.event.pump()
    # Aura 7.1.1: allow the launcher to stop the controller bridge.
    # SDL may otherwise turn SIGTERM into a QUIT event ignored by this loop.
    import signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    configs = []
    for path in ['/userdata/system/configs/emulationstation/es_input.cfg', '/usr/share/emulationstation/es_input.cfg']:
        try:
            configs.extend(ET.parse(path).getroot().findall('inputConfig'))
        except (OSError, ET.ParseError) as error:
            print('[CONTROLE] Configuracao:', path, type(error).__name__, flush=True)
    CALIBRATION_STATUS.unlink(missing_ok=True)
    calibrations = {}
    devices = {}
    pads = {}
    def add(index):
        joy = pygame.joystick.Joystick(index)
        joy.init()
        if joy.get_instance_id() in devices: return
        bindings = mapping(configs, joy.get_guid(), joy.get_name())
        # Use SDL's full mapping, including d-pad and axes, for recognized pads.
        try:
            from pygame._sdl2 import controller
            controller.init()
            if controller.is_controller(index):
                pad = controller.Controller(index)
                sdl = pad.get_mapping()
                names = {'a':'a','b':'b','x':'x','y':'y','start':'start','back':'select',
                         'dpup':'up','dpdown':'down','dpleft':'left','dpright':'right',
                         'leftx':'joystick1left','lefty':'joystick1up'}
                for name, dest in names.items():
                    value = sdl.get(name, '')
                    spec = sdl_binding(value, dest)
                    if spec is not None: bindings[dest] = spec
                # Retain this handle: closing it can invalidate the joystick.
                pads[joy.get_instance_id()] = pad
        except (ImportError, pygame.error, AttributeError, ValueError):
            print('[CONTROLE] SDL indisponivel; usando cadastro ES.', flush=True)
        calibrations[joy.get_instance_id()] = ButtonCalibration(joy.get_guid()+':'+joy.get_name(),bindings)
        devices[joy.get_instance_id()] = (joy, bindings, Repeater())
        print('[CONTROLE]', joy.get_name(), 'A/B configurados:', 'a' in bindings and 'b' in bindings, flush=True)
    for index in range(pygame.joystick.get_count()):
        add(index)
    # Verify event processing before reporting readiness to the launcher.
    # Keep listening for controllers connected after the browser opens.
    pygame.event.pump()
    print('[CONTROLE] Aguardando entradas; controles:', len(devices), flush=True)
    ready.write_text('ready')
    focused, check_at = False, 0
    pointer=False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                add(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                devices.pop(event.instance_id, None)
                calibrations.pop(event.instance_id, None)
                pad = pads.pop(event.instance_id, None)
                if pad is not None: pad.quit()
        now = time.monotonic()
        if now >= check_at:
            focused, check_at = browser_focused(), now + .5
        for joy, bindings, repeater in devices.values():
            try:
                calibration=calibrations[joy.get_instance_id()]
                if not calibration.finished:
                    if focused:
                        calibration.step([i for i in range(joy.get_numbuttons()) if joy.get_button(i)])
                    repeater.step('',now)
                    continue
                key = action(joy, bindings)
                # Track held keys even outside Chromium: returning focus does
                # not replay A/B, and key release is always paired by xdotool.
                fire = repeater.step(key, now)
                if fire and focused and browser_focused():
                    if key=='F2':
                        pointer=not pointer
                        print('[CONTROLE] Modo ponteiro:',pointer,flush=True)
                        subprocess.run(['xdotool','key','--clearmodifiers','F2'],timeout=2,check=False)
                    elif pointer and key in ('Up','Down','Left','Right'):
                        dx,dy={'Up':(0,-35),'Down':(0,35),'Left':(-35,0),'Right':(35,0)}[key]
                        subprocess.run(['xdotool','mousemove_relative','--',str(dx),str(dy)],timeout=2,check=False)
                    elif pointer and key=='Return':
                        subprocess.run(['xdotool','click','1'],timeout=2,check=False)
                    else:
                        subprocess.run(['xdotool', 'key', '--clearmodifiers', key], timeout=2, check=False)
            except (pygame.error, OSError, subprocess.SubprocessError) as error:
                print('[CONTROLE]', type(error).__name__, str(error), flush=True)
        time.sleep(.016)


if __name__ == '__main__':
    main()
