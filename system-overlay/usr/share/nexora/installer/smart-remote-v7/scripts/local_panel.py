"""Local-only approval UI over a mode-0600 UNIX socket. Never served over HTTP."""
import json
import os
from pathlib import Path
import socket
import sys
import time
import subprocess
import traceback

ROOT=Path(__file__).resolve().parents[1]

def call(action,**kw):
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3);sock.connect(str(ROOT/'run/admin.sock'))
        sock.sendall((json.dumps({'action':action,**kw})+'\n').encode())
        return json.loads(sock.makefile('r').readline())

def panel():
    os.environ.setdefault('DISPLAY',':0')
    import pygame
    import qrcode
    call('pause',enabled=True)
    pygame.init()
    screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
    pygame.display.set_caption('Nexora Remote — pareamento local')
    pygame.mouse.set_visible(False)
    width,height=screen.get_size()
    scale=min(width/960,height/640)
    offset=((width-960*scale)/2,(height-640*scale)/2)
    def position(pos):return (round(offset[0]+pos[0]*scale),round(offset[1]+pos[1]*scale))
    font=pygame.font.Font(None,max(12,round(30*scale)))
    large=pygame.font.Font(None,max(24,round(72*scale)))
    known_sessions=set();pairing=None;qr=None;until=0;state={};last=0;selected=0;running=True;message=''
    def text(s,pos,color=(237,243,255),f=font):screen.blit(f.render(s,True,color),position(pos))
    def open_pin():
        nonlocal known_sessions,pairing,until,qr,message
        known_sessions={x['id'] for x in call('status').get('sessions',[])}
        result=call('open')
        if 'pin' not in result:
            pairing=None;until=time.monotonic()+120
            message='Limite de dispositivos. Revogue uma sessão para vincular outro.'
            return
        pairing=result;until=time.monotonic()+result['expires']
        code=qrcode.QRCode(box_size=1,border=4)
        code.add_data(pairing['url']);code.make(fit=True)
        code.box_size=max(1,int(240*scale)//(code.modules_count+8))
        image=code.make_image().convert('RGB')
        qr=pygame.image.fromstring(image.tobytes(),image.size,'RGB')
    open_pin()
    while running:
        now=time.monotonic()
        if now-last>0.5:
            state=call('status');last=now
            if pairing and {x['id'] for x in state.get('sessions',[])}-known_sessions:
                running=False;break
        if now>=until:open_pin()
        for e in pygame.event.get():
            if e.type==pygame.QUIT:running=False
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE:running=False
                if e.key==pygame.K_p:
                    open_pin()
                if e.key==pygame.K_RETURN and state.get('pending'):
                    call('approve',id=state['pending'][0]['id']);message='Celular aprovado. Pode fechar esta janela para controlar o menu.'
                if e.key==pygame.K_r:call('revoke');message='Todas as sessões revogadas.';pairing=None
                if e.key in (pygame.K_DOWN,pygame.K_UP):selected+=1 if e.key==pygame.K_DOWN else -1
                if e.key==pygame.K_DELETE and state.get('sessions'):
                    call('revoke',id=state['sessions'][selected%len(state['sessions'])]['id'])
        screen.fill((9,12,20));text('NEXORA REMOTE · V8.6',(30,22),(234,169,91))
        text('Leia o QR e digite o PIN no celular. Não precisa de teclado.',(30,64))
        text('Digite o PIN no celular para vincular. QR não contém senha.',(30,102))
        if pairing and now<until:
            screen.blit(qr,position((30,155)));text(pairing['pin'],(315,160),f=large)
            text(pairing['url'],(315,244));text(f'Expira em {max(0,int(until-now))} segundos',(315,284))
        else:text('Não foi possível gerar um PIN. Veja a mensagem abaixo.',(30,165))
        pending=state.get('pending',[])
        if pending:text('Aprovar: '+pending[0]['name']+' · '+pending[0]['ip'],(30,418),(255,201,133))
        text('CONTROLE ATIVO' if state.get('active') else 'Sem controlador ativo',(30,460),(120,220,170))
        sessions=state.get('sessions',[])
        if sessions:
            row=sessions[selected%len(sessions)]
            text(f"Dispositivo {selected%len(sessions)+1}/{len(sessions)}: {row['name']} — Del: revogar",(30,501))
        text(message[:92],(30,548));text('HTTP: tráfego em claro. Use uma rede local confiável.',(30,595),(134,146,165))
        pygame.display.flip();pygame.time.wait(30)
    call('pause',enabled=False)
    pygame.quit()

if __name__=='__main__':
    if len(sys.argv)>1:
        # Explicit local CLI alternative; open prints PIN only in operator terminal.
        print(json.dumps(call(sys.argv[1],**({'id':sys.argv[2]} if len(sys.argv)>2 else {}))))
    else:
        log=ROOT/'logs/panel.log'
        log.parent.mkdir(parents=True,exist_ok=True)
        try:
            try:call('status')
            except (OSError,ValueError):
                subprocess.run(['bash','/userdata/system/services/batocera_smart_remote','start'],check=True,timeout=15)
                call('status')
            panel()
        except Exception:
            with log.open('a') as stream:
                stream.write('\n'+time.strftime('%Y-%m-%d %H:%M:%S')+'\n')
                traceback.print_exc(file=stream)
            traceback.print_exc()
        finally:
            try:call('pause',enabled=False)
            except Exception:pass
            # Export the actual panel failure for diagnosis on Windows.
            diagnostic=Path('/boot/aura-installer/home-row/diagnose.sh')
            if diagnostic.is_file():
                try:subprocess.run(['bash',str(diagnostic)],timeout=20,check=False)
                except subprocess.TimeoutExpired:pass
