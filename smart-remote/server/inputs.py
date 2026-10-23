"""Linux input adapter: independent keyboard/mouse and Xbox-layout gamepad."""
import asyncio
import math
import os
import shutil

KEYS = {'UP':103,'DOWN':108,'LEFT':105,'RIGHT':106,'SELECT':28,'BACK':1,'MENU':57,
        'ENTER':28,'ESCAPE':1,'VOLUME_UP':115,'VOLUME_DOWN':114,'PLAY_PAUSE':164,
        'MOUSE_LEFT':272,'MOUSE_RIGHT':273}
GAME = {'A':304,'B':305,'X':307,'Y':308,'L1':310,'R1':311,'SELECT_GAME':314,'START':315,'L3':317,'R3':318}
HATS = {'GP_LEFT':(-1,0),'GP_RIGHT':(1,0),'GP_UP':(0,-1),'GP_DOWN':(0,1)}
MODES = ('remote','gamepad','mouse','apps')


class Inputs:
    def __init__(self, fake=False):
        self.fake = fake
        self.events = []
        self.held = set()
        self.mode = 'remote'
        self.axes = {}
        self.deadzone = 0.12
        if not fake:
            from evdev import UInput, AbsInfo, ecodes as e
            self.keyboard = UInput({e.EV_KEY:list(set(KEYS.values())), e.EV_REL:[e.REL_X,e.REL_Y,e.REL_WHEEL]}, name='Batocera Smart Remote Keyboard')
            axes = [(c,AbsInfo(0,-32767,32767,0,0,0)) for c in (0,1,3,4)]
            axes += [(c,AbsInfo(0,0,255,0,0,0)) for c in (2,5)]
            axes += [(c,AbsInfo(0,-1,1,0,0,0)) for c in (16,17)]
            self.gamepad = UInput({e.EV_KEY:list(GAME.values()),e.EV_ABS:axes},name='Batocera Smart Remote Gamepad',vendor=0x045e,product=0x028e,version=0x0114,bustype=3)

    def emit(self, target, typ, code, value):
        if self.fake:
            self.events.append((target,typ,code,value))
            self.events = self.events[-2000:]
        else:
            device = self.gamepad if target=='gamepad' else self.keyboard
            device.write(typ,code,value)
            device.syn()

    def button(self, control, phase):
        if phase not in ('down','up'):
            raise ValueError('Fase inválida.')
        allowed = set(GAME)|set(HATS)|{'L2','R2'} if self.mode=='gamepad' else set(KEYS)|{'SCROLL_UP','SCROLL_DOWN'}
        if control not in allowed:
            raise ValueError('Comando indisponível neste modo.')
        down = phase=='down'
        if down == (control in self.held):
            return
        if down:self.held.add(control)
        else:self.held.discard(control)
        if control in GAME:self.emit('gamepad',1,GAME[control],int(down))
        elif control in HATS:
            x=sum(HATS[c][0] for c in self.held if c in HATS)
            y=sum(HATS[c][1] for c in self.held if c in HATS)
            self.emit('gamepad',3,16,x);self.emit('gamepad',3,17,y)
        elif control in ('L2','R2'):self.emit('gamepad',3,2 if control=='L2' else 5,255 if down else 0)
        elif control.startswith('SCROLL_'):
            if down:self.emit('keyboard',2,8,1 if control=='SCROLL_UP' else -1)
        else:self.emit('keyboard',1,KEYS[control],int(down))

    def axis(self, stick, x, y):
        if self.mode!='gamepad' or stick not in ('LEFT','RIGHT'):
            raise ValueError('Eixo inválido.')
        if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1 for v in (x,y)):
            raise ValueError('Eixo fora do intervalo.')
        magnitude=math.hypot(x,y)
        gain=0 if magnitude<=self.deadzone else (min(magnitude,1)-self.deadzone)/((1-self.deadzone)*magnitude)
        codes=(0,1) if stick=='LEFT' else (3,4)
        for code,v in zip(codes,(x,y)):
            value=round(v*gain*32767)
            self.axes[code]=value
            if self.fake:self.emit('gamepad',3,code,value)
            else:self.gamepad.write(3,code,value)
        if not self.fake:self.gamepad.syn()

    def release(self):
        for c in tuple(self.held):self.button(c,'up')
        for code in (0,1,2,3,4,5,16,17):self.emit('gamepad',3,code,0)
        self.axes.clear()

    async def command(self, m):
        typ=m.get('type')
        if typ=='release_all':self.release()
        elif typ=='mode':
            if m.get('mode') not in MODES:raise ValueError('Modo inválido.')
            self.release();self.mode=m['mode']
        elif typ=='button':self.button(m.get('control'),m.get('phase'))
        elif typ=='axis':self.axis(m.get('stick'),m.get('x'),m.get('y'))
        elif typ=='mouse_move':
            if self.mode!='mouse':raise ValueError('Ative Mouse.')
            for code,k in ((0,'dx'),(1,'dy')):
                v=m.get(k)
                if type(v)!=int or abs(v)>500:raise ValueError('Movimento inválido.')
            self.emit('keyboard',2,0,m['dx']);self.emit('keyboard',2,1,m['dy'])
        elif typ=='type_text':
            text=m.get('text')
            if self.mode!='mouse' or not isinstance(text,str) or not 0<len(text)<=500 or any(ord(c)<32 for c in text):
                raise ValueError('Texto inválido (máximo 500 caracteres).')
            if not self.fake:
                if not shutil.which('xdotool'):raise ValueError('Digitação requer X11 e xdotool.')
                proc=await asyncio.create_subprocess_exec('xdotool','type','--clearmodifiers','--delay','1','--',text,env={**os.environ,'DISPLAY':os.environ.get('DISPLAY',':0')},stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                try:await asyncio.wait_for(proc.wait(),3)
                except asyncio.TimeoutError:proc.kill();await proc.wait();raise ValueError('Digitação excedeu o tempo.')
                if proc.returncode:raise ValueError('Não foi possível digitar na sessão X11.')
        else:raise ValueError('Evento desconhecido.')

    def close(self):
        self.release()
        if not self.fake:self.gamepad.close();self.keyboard.close()
