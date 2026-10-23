#!/usr/bin/env python3
from pathlib import Path
import pygame, subprocess, threading, queue, json, re, time, os, pty, select, signal, shutil, xml.etree.ElementTree as ET

BASE=Path('/userdata/system/aura-store-native')
HERE=BASE
CATALOG=HERE/'catalog.json'
LOG=HERE/'aura-store.log'
STATE=HERE/'state.json'
PORTS=Path('/userdata/roms/ports')
PORTS_IMAGES=PORTS/'images'
PORTS_GAMELIST=PORTS/'gamelist.xml'
APPS=Path('/userdata/roms/apps')

BG=(5,12,22); TOP=(7,18,31); PANEL=(10,25,42); PANEL2=(14,36,59)
TEXT=(244,248,255); MUTED=(145,167,190); CYAN=(57,218,255); PURPLE=(171,96,255)
GREEN=(87,230,169); YELLOW=(247,202,95); RED=(255,119,145); BORDER=(35,70,99)

ANSI=re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
PERCENT=re.compile(r'(?<!\d)(100|[1-9]?\d)%')


def log(msg):
    try:
        BASE.mkdir(parents=True,exist_ok=True)
        with LOG.open('a',encoding='utf-8') as f:
            f.write(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}\n')
    except Exception: pass


def run(args,timeout=45):
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',timeout=timeout)
        return p.returncode,p.stdout.strip()
    except Exception as e:return 99,str(e)


def flatpak_ids():
    rc,out=run(['flatpak','list','--app','--columns=application'],60)
    return {x.strip() for x in out.splitlines() if x.strip()} if rc==0 else set()


def has_remote():
    rc,out=run(['flatpak','remotes','--columns=name'],30)
    return rc==0 and any(x.strip()=='flathub' for x in out.splitlines())


def ensure_flathub():
    if has_remote(): return
    rc,out=run(['flatpak','remote-add','--system','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo'],180)
    if rc!=0: raise RuntimeError(out or 'Não foi possível configurar o Flathub.')


def aura_shortcut_exists(app):
    return (APPS/app.get('shortcut','')).is_file() if app.get('shortcut') else False


def installed(app,fp=None):
    if app['kind']=='aura_app': return aura_shortcut_exists(app)
    fp=fp if fp is not None else flatpak_ids()
    return app.get('appid') in fp


def sanitize(s):
    return re.sub(r'[^A-Za-z0-9 ._()+-]+',' ',s).strip()[:60] or 'App'


def launcher_path(app):
    return PORTS/(sanitize(app['name'])+' (Aura).sh')


def remove_old_managed_entries(app):
    # Remove apenas wrappers gerenciados por versões antigas do Aura Native.
    for p in PORTS.glob(sanitize(app['name'])+'*.sh'):
        try:
            txt=p.read_text(errors='replace')
            if '# aura-store-native-managed' in txt and p!=launcher_path(app): p.unlink()
        except Exception: pass


def make_icon(app):
    PORTS_IMAGES.mkdir(parents=True,exist_ok=True)
    path=PORTS_IMAGES/(sanitize(app['name']).replace(' ','_').lower()+'-aura-native.png')
    try:
        surf=pygame.Surface((600,600)); surf.fill((7,18,31))
        pygame.draw.circle(surf,(19,51,78),(300,300),220)
        pygame.draw.circle(surf,CYAN,(300,300),220,10)
        f=pygame.font.SysFont('DejaVu Sans',180,bold=True)
        initials=''.join(x[0] for x in app['name'].split()[:2]).upper()[:2]
        t=f.render(initials,True,TEXT); surf.blit(t,t.get_rect(center=(300,300)))
        pygame.image.save(surf,str(path))
        return path
    except Exception:return None


def update_ports_gamelist(app,script,icon=None):
    PORTS.mkdir(parents=True,exist_ok=True)
    if PORTS_GAMELIST.exists():
        try:tree=ET.parse(PORTS_GAMELIST);root=tree.getroot()
        except Exception:root=ET.Element('gameList');tree=ET.ElementTree(root)
    else:root=ET.Element('gameList');tree=ET.ElementTree(root)
    rel='./'+script.name
    # Limpa entradas antigas gerenciadas para o mesmo app.
    for g in list(root.findall('game')):
        n=(g.findtext('name') or '').strip().lower()
        p=(g.findtext('path') or '').strip().lower()
        if app['name'].lower() in n and '(aura)' in p and p!=rel.lower(): root.remove(g)
    g=next((x for x in root.findall('game') if (x.findtext('path') or '').strip()==rel),None)
    if g is None:g=ET.SubElement(root,'game')
    vals={'path':rel,'name':app['name'],'desc':app.get('summary',''),'developer':'Batocera Aura','genre':app.get('category','Apps')}
    if icon:
        vals['image']='./images/'+icon.name; vals['thumbnail']='./images/'+icon.name
    for k,v in vals.items():
        e=g.find(k)
        if e is None:e=ET.SubElement(g,k)
        e.text=v
    tree.write(PORTS_GAMELIST,encoding='UTF-8',xml_declaration=True)


def create_flatpak_launcher(app):
    # Reconcile by application ID; never recreate duplicate PORTS launchers.
    from reconcile import reconcile
    reconcile()


class FlatpakWorker:
    def __init__(self,app,q):
        self.app=app; self.q=q; self.proc=None; self.cancelled=False
    def emit(self,kind,**kw): self.q.put((kind,kw))
    def cancel(self):
        self.cancelled=True
        try:self.proc.terminate()
        except Exception:pass
    def run(self):
        app=self.app; appid=app['appid']
        try:
            self.emit('progress',percent=2,text='Verificando Flathub...')
            ensure_flathub()
            rc,info=run(['flatpak','remote-info','flathub',appid],180)
            if rc!=0: raise RuntimeError(info or 'Pacote não encontrado no Flathub.')
            self.emit('progress',percent=5,text='Preparando instalação...')
            master,slave=pty.openpty()
            cmd=['flatpak','install','--or-update','-y','--noninteractive','flathub',appid]
            self.proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=slave,stderr=slave,close_fds=True)
            os.close(slave)
            buf=''; last=5; last_text='Instalando...'
            while self.proc.poll() is None:
                r,_,_=select.select([master],[],[],0.2)
                if not r: continue
                try:data=os.read(master,4096).decode('utf-8','replace')
                except OSError:break
                buf+=data.replace('\r','\n')
                parts=buf.split('\n'); buf=parts.pop()
                for raw in parts:
                    s=ANSI.sub('',raw).strip()
                    if not s: continue
                    last_text=s[-120:]
                    m=PERCENT.search(s)
                    if m:
                        p=int(m.group(1)); last=max(last,min(98,p))
                    self.emit('progress',percent=last,text=last_text)
            try:os.close(master)
            except Exception:pass
            rc=self.proc.wait()
            if self.cancelled: raise RuntimeError('Instalação cancelada.')
            if rc!=0: raise RuntimeError(last_text or f'Flatpak terminou com código {rc}.')
            self.emit('progress',percent=99,text='Criando atalho no Batocera...')
            create_flatpak_launcher(app)
            self.emit('done',percent=100,text='Instalado com sucesso.')
        except Exception as e:
            log('install error '+appid+': '+repr(e)); self.emit('error',text=str(e))


class AuraStore:
    def __init__(self):
        pygame.init(); pygame.font.init(); pygame.joystick.init()
        self.screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        self.w,self.h=self.screen.get_size(); pygame.display.set_caption('Batocera Store Native · Aura')
        self.clock=pygame.time.Clock(); self.apps=json.loads(CATALOG.read_text(encoding='utf-8'))['apps']
        self.font={k:pygame.font.SysFont('DejaVu Sans',sz,bold=b) for k,sz,b in [('xs',15,False),('sm',18,False),('md',23,False),('lg',32,True),('xl',45,True)]}
        self.selected=0; self.detail=False; self.filter='Todos'; self.filters=['Todos','Streaming','Flatpak','Instalados']; self.search='' 
        self.jobq=queue.Queue(); self.worker=None; self.job=False; self.percent=0; self.jobtext=''; self.notice=''; self.notice_until=0
        self.inst=flatpak_ids(); self.joys={}; self.axis_ts=0
        self.scan_joys(); self.refresh()
    def scan_joys(self):
        self.joys={}
        for i in range(pygame.joystick.get_count()):
            try:
                j=pygame.joystick.Joystick(i);j.init();self.joys[j.get_instance_id()]=j
            except Exception:pass
    def refresh(self):
        self.inst=flatpak_ids()
        for a in self.apps:a['_installed']=installed(a,self.inst)
        self.view=self.filtered(); self.selected=max(0,min(self.selected,max(0,len(self.view)-1)))
    def filtered(self):
        rows=list(self.apps)
        if self.filter=='Streaming': rows=[a for a in rows if a['kind']=='aura_app']
        elif self.filter=='Flatpak': rows=[a for a in rows if a['kind']=='flatpak']
        elif self.filter=='Instalados': rows=[a for a in rows if a.get('_installed')]
        q=self.search.strip().lower()
        if q: rows=[a for a in rows if q in (a.get('name','')+' '+a.get('summary','')+' '+a.get('appid','')).lower()]
        return rows
    def tx(self,s,k,c=TEXT):return self.font[k].render(str(s),True,c)
    def wrap(self,s,k,w):
        f=self.font[k]; out=[]; line=''
        for word in str(s).split():
            t=(line+' '+word).strip()
            if f.size(t)[0]<=w:line=t
            else:
                if line:out.append(line)
                line=word
        if line:out.append(line)
        return out
    def header(self):
        pygame.draw.rect(self.screen,TOP,(0,0,self.w,102)); pygame.draw.line(self.screen,CYAN,(0,101),(self.w,101),2)
        pygame.draw.rect(self.screen,(10,34,55),(30,21,58,58),border_radius=16); pygame.draw.rect(self.screen,CYAN,(30,21,58,58),2,border_radius=16)
        pygame.draw.circle(self.screen,PURPLE,(59,50),16); pygame.draw.circle(self.screen,CYAN,(59,50),10)
        self.screen.blit(self.tx('Batocera Store','lg'),(108,20)); self.screen.blit(self.tx('AURA NATIVE · OFFLINE UI','xs',MUTED),(110,61)); self.screen.blit(self.tx('Buscar: '+(self.search or 'digite para pesquisar'),'xs',CYAN if self.search else MUTED),(360,61))
        r=pygame.Rect(self.w-235,31,195,38); pygame.draw.rect(self.screen,(12,34,54),r,border_radius=10)
        status='FLATHUB OK' if has_remote() else 'OFFLINE / SEM FLATHUB'
        col=GREEN if has_remote() else YELLOW
        self.screen.blit(self.tx(status,'xs',col),self.tx(status,'xs',col).get_rect(center=r.center))
    def filterbar(self):
        x=32; y=118
        for f in self.filters:
            active=f==self.filter; t=self.tx(f,'sm',TEXT if active else MUTED); r=pygame.Rect(x,y,t.get_width()+28,38)
            pygame.draw.rect(self.screen,PANEL2 if active else PANEL,r,border_radius=10); pygame.draw.rect(self.screen,CYAN if active else BORDER,r,2 if active else 1,border_radius=10)
            self.screen.blit(t,t.get_rect(center=r.center)); x=r.right+10
    def grid_metrics(self):
        cols=3; gap=16; left=32; top=176; bottom=76; rows=3
        cw=(self.w-left*2-gap*(cols-1))//cols; ch=(self.h-top-bottom-gap*(rows-1))//rows
        return cols,rows,gap,left,top,cw,ch
    def page(self):
        cols,rows,*_=self.grid_metrics(); per=cols*rows; return self.selected//per,per
    def cardrect(self,screen_idx):
        cols,rows,gap,left,top,cw,ch=self.grid_metrics(); return pygame.Rect(left+(screen_idx%cols)*(cw+gap),top+(screen_idx//cols)*(ch+gap),cw,ch)
    def draw_card(self,a,si,absolute_idx):
        r=self.cardrect(si); sel=absolute_idx==self.selected and not self.detail and not self.job
        pygame.draw.rect(self.screen,PANEL2 if sel else PANEL,r,border_radius=16); pygame.draw.rect(self.screen,CYAN if sel else BORDER,r,3 if sel else 1,border_radius=16)
        badge='INSTALADO' if a['_installed'] else ('AURA APP' if a['kind']=='aura_app' else 'FLATPAK')
        bc=GREEN if a['_installed'] else CYAN if a['kind']=='aura_app' else PURPLE
        self.screen.blit(self.tx(badge,'xs',bc),(r.x+18,r.y+15)); self.screen.blit(self.tx(a['name'],'md'),(r.x+18,r.y+45))
        self.screen.blit(self.tx(a['category'],'xs',MUTED),(r.x+18,r.y+78)); y=r.y+105
        for line in self.wrap(a['summary'],'xs',r.width-36)[:2]:self.screen.blit(self.tx(line,'xs',MUTED),(r.x+18,y));y+=19
    def draw_main(self):
        self.screen.fill(BG); self.header(); self.filterbar();
        pg,per=self.page(); start=pg*per; subset=self.view[start:start+per]
        for si,a in enumerate(subset):self.draw_card(a,si,start+si)
        footer='Setas/D-pad navegar · A/Enter detalhes · X filtros · Digite para buscar · Del limpa · B/Esc sair'
        self.screen.blit(self.tx(footer,'sm',MUTED),(32,self.h-46))
        if len(self.view)>per:
            pages=(len(self.view)+per-1)//per; ptxt=f'Página {pg+1}/{pages}'
            t=self.tx(ptxt,'sm',MUTED);self.screen.blit(t,(self.w-t.get_width()-32,self.h-46))
        self.draw_notice()
    def draw_detail(self):
        self.draw_main(); ov=pygame.Surface((self.w,self.h),pygame.SRCALPHA);ov.fill((0,0,0,175));self.screen.blit(ov,(0,0))
        a=self.view[self.selected]; box=pygame.Rect(int(self.w*.17),int(self.h*.15),int(self.w*.66),int(self.h*.68))
        pygame.draw.rect(self.screen,(8,24,42),box,border_radius=22);pygame.draw.rect(self.screen,CYAN,box,2,border_radius=22)
        self.screen.blit(self.tx(a['category'].upper(),'xs',CYAN),(box.x+36,box.y+30));self.screen.blit(self.tx(a['name'],'xl'),(box.x+36,box.y+62))
        y=box.y+130
        for line in self.wrap(a['summary'],'md',box.width-72)[:4]:self.screen.blit(self.tx(line,'md',MUTED),(box.x+36,y));y+=29
        y+=14
        if a['kind']=='aura_app':
            info='Use teclado/mouse. Alt+F4 para sair.' if a['_installed'] else 'Aguarde a configuração do Aura ou reinicie.'
            action='A · ABRIR' if a['_installed'] else 'AGUARDANDO CONFIGURAÇÃO'
            enabled=a['_installed']
        elif a['kind']=='rgsx':
            info='Atalho local encontrado.' if a['_installed'] else 'Nenhum atalho local encontrado. Não será baixado automaticamente.'
            action='A · ABRIR' if a['_installed'] else 'NÃO INSTALADO'
            enabled=a['_installed']
        else:
            info='Aplicativo Flatpak instalado.' if a['_installed'] else 'Pode ser instalado pelo Flathub diretamente nesta loja.'
            action='A · ABRIR' if a['_installed'] else 'A · INSTALAR'
            enabled=True
        self.screen.blit(self.tx(info,'sm',TEXT),(box.x+36,y));
        btn=pygame.Rect(box.x+36,box.bottom-88,box.width-72,52);self.action_rect=btn;pygame.draw.rect(self.screen,(28,92,113) if enabled else (43,57,70),btn,border_radius=12)
        t=self.tx(action,'md',TEXT if enabled else MUTED);self.screen.blit(t,t.get_rect(center=btn.center))
        b=self.tx('B · voltar','sm',MUTED);self.screen.blit(b,(box.right-b.get_width()-36,box.y+32)); self.draw_notice()
    def draw_progress(self):
        self.draw_detail(); ov=pygame.Surface((self.w,self.h),pygame.SRCALPHA);ov.fill((0,0,0,195));self.screen.blit(ov,(0,0))
        box=pygame.Rect(int(self.w*.22),int(self.h*.31),int(self.w*.56),int(self.h*.34));pygame.draw.rect(self.screen,(8,24,42),box,border_radius=20);pygame.draw.rect(self.screen,PURPLE,box,2,border_radius=20)
        a=self.view[self.selected]; self.screen.blit(self.tx('Instalando '+a['name'],'lg'),(box.x+34,box.y+30))
        self.screen.blit(self.tx(self.jobtext or 'Preparando...','sm',MUTED),(box.x+34,box.y+88))
        bar=pygame.Rect(box.x+34,box.y+132,box.width-68,30);pygame.draw.rect(self.screen,(25,43,58),bar,border_radius=10)
        fill=bar.copy();fill.width=int(bar.width*max(0,min(100,self.percent))/100);pygame.draw.rect(self.screen,CYAN,fill,border_radius=10)
        p=self.tx(f'{self.percent}%','lg',TEXT);self.screen.blit(p,p.get_rect(center=(box.centerx,box.y+195)))
        c=self.tx('B · cancelar','sm',MUTED);self.screen.blit(c,c.get_rect(center=(box.centerx,box.bottom-28)))
    def draw_notice(self):
        if not self.notice or time.time()>self.notice_until:return
        t=self.tx(self.notice,'sm',TEXT);r=pygame.Rect(40,self.h-94,min(self.w-80,t.get_width()+32),40);pygame.draw.rect(self.screen,(13,39,60),r,border_radius=10);self.screen.blit(t,(r.x+16,r.y+10))
    def notify(self,s,sec=5):self.notice=str(s);self.notice_until=time.time()+sec
    def move(self,dx,dy):
        if not self.view:return
        cols,rows,*_=self.grid_metrics(); idx=self.selected; row=idx//cols; col=idx%cols
        ni=idx+dx+dy*cols; ni=max(0,min(len(self.view)-1,ni));self.selected=ni
    def next_filter(self):
        i=(self.filters.index(self.filter)+1)%len(self.filters);self.filter=self.filters[i];self.view=self.filtered();self.selected=0
    def start_action(self):
        if not self.view:return
        a=self.view[self.selected]
        if a['kind']=='aura_app':
            script=APPS/a.get('shortcut','')
            if not script.is_file():
                self.notify('Aguarde a configuração ou use Aura - Reparar streaming em PORTS.',8)
                return
            pygame.quit()
            os.execvp('python3',['python3',str(BASE/'app_runner.py'),str(script)])
        if a['kind']!='flatpak':return
        if a['_installed']:
            script=APPS/(a['appid']+'.app')
            if script.is_file():
                pygame.quit();os.execvp('python3',['python3',str(BASE/'app_runner.py'),str(script)])
            else:
                self.notify('Atualize os atalhos reabrindo a loja.',6)
            return
        self.job=True;self.percent=0;self.jobtext='Preparando...';self.worker=FlatpakWorker(a,self.jobq);threading.Thread(target=self.worker.run,daemon=True).start()
    def jobs(self):
        while True:
            try:k,d=self.jobq.get_nowait()
            except queue.Empty:break
            if k=='progress':self.percent=int(d.get('percent',self.percent));self.jobtext=d.get('text','')
            elif k=='done':self.percent=100;self.jobtext=d.get('text','');self.job=False;self.refresh();self.notify('Instalação concluída. Atualize a lista de jogos para ver o atalho.',7)
            elif k=='error':self.job=False;self.notify('Erro: '+d.get('text',''),10)
    def handle_button(self,b):
        if self.job:
            if b==1 and self.worker:self.worker.cancel()
            return True
        # Padrão Xbox/SDL mais comum: A0 B1 X2 Start7.
        if b==0:
            if self.detail:self.start_action()
            else:self.detail=True
        elif b==1:
            if self.job and self.worker:self.worker.cancel()
            elif self.detail:self.detail=False
            else:return False
        elif b==2 and not self.detail:self.next_filter()
        return True
    def loop(self):
        running=True
        while running:
            self.jobs()
            for e in pygame.event.get():
                if e.type==pygame.QUIT:running=False
                elif e.type==pygame.JOYDEVICEADDED:self.scan_joys()
                elif e.type==pygame.JOYDEVICEREMOVED:self.scan_joys()
                elif e.type==pygame.JOYBUTTONDOWN:
                    if self.handle_button(e.button) is False:running=False
                elif e.type==pygame.JOYHATMOTION and not self.job:
                    x,y=e.value
                    if x:self.move(x,0)
                    if y:self.move(0,-y)
                elif e.type==pygame.JOYAXISMOTION and not self.job and time.time()-self.axis_ts>.22:
                    if e.axis==0 and abs(e.value)>.65:self.move(1 if e.value>0 else -1,0);self.axis_ts=time.time()
                    if e.axis==1 and abs(e.value)>.65:self.move(0,1 if e.value>0 else -1);self.axis_ts=time.time()
                elif e.type==pygame.KEYDOWN:
                    if self.job:
                        if e.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE) and self.worker:self.worker.cancel()
                        continue
                    if e.key==pygame.K_BACKSPACE and not self.detail and self.search:
                        self.search=self.search[:-1]; self.view=self.filtered(); self.selected=0
                    elif e.key==pygame.K_DELETE and not self.detail:
                        self.search=''; self.view=self.filtered(); self.selected=0
                    elif e.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                        if self.detail:self.detail=False
                        else:running=False
                    elif e.key in (pygame.K_RETURN,pygame.K_SPACE):
                        if self.detail:self.start_action()
                        else:self.detail=True
                    elif e.key==pygame.K_PAGEUP and not self.detail:self.move(0,-self.grid_metrics()[1])
                    elif e.key==pygame.K_PAGEDOWN and not self.detail:self.move(0,self.grid_metrics()[1])
                    elif e.key==pygame.K_HOME and not self.detail:self.selected=0
                    elif e.key==pygame.K_END and not self.detail:self.selected=max(0,len(self.view)-1)
                    elif e.key==pygame.K_LEFT:self.move(-1,0)
                    elif e.key==pygame.K_RIGHT:self.move(1,0)
                    elif e.key==pygame.K_UP:self.move(0,-1)
                    elif e.key==pygame.K_DOWN:self.move(0,1)
                    elif e.key in (pygame.K_x,pygame.K_TAB):self.next_filter()
                    elif not self.detail and getattr(e,'unicode','') and e.unicode.isprintable() and not e.unicode.isspace() and len(self.search)<48:
                        self.search+=e.unicode; self.view=self.filtered(); self.selected=0
                elif e.type==pygame.MOUSEWHEEL and not self.job and not self.detail:
                    self.move(0,-e.y)
                elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and not self.job:
                    if self.detail:
                        if getattr(self,'action_rect',pygame.Rect(0,0,0,0)).collidepoint(e.pos):self.start_action()
                    else:
                        pg,per=self.page();start=pg*per
                        for si,a in enumerate(self.view[start:start+per]):
                            if self.cardrect(si).collidepoint(e.pos):self.selected=start+si;self.detail=True;break
            if self.job:self.draw_progress()
            elif self.detail:self.draw_detail()
            else:self.draw_main()
            pygame.display.flip();self.clock.tick(60)
        pygame.quit()

if __name__=='__main__':
    try:AuraStore().loop()
    except Exception as e:
        log('fatal '+repr(e));raise
