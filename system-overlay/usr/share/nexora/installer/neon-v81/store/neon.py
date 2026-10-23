#!/usr/bin/env python3
"""AURA Neon: responsive, offline-rendered store; existing install engine retained."""
import os, time, platform
from pathlib import Path
import pygame
from main import AuraStore, BASE, TEXT, MUTED, CYAN, GREEN, BORDER, PANEL, installed


class NeonStore(AuraStore):
    def __init__(self):
        super().__init__()
        self.display = self.screen
        self.screen = pygame.Surface((1600, 900))
        self.w, self.h = self.screen.get_size()
        self.font = {k: pygame.font.Font(str(BASE/'assets/fonts'/('Cabin-Bold.ttf' if b else 'Cabin-Regular.ttf')), sz) for k,sz,b in
                     [('xs',16,False),('sm',19,False),('md',25,False),('lg',31,True),('xl',44,True)]}
        self.filters = ['Home','Apps','Streaming','RGSX','Instalados','Meu PC']
        paths=sorted(p for p in Path('/userdata/roms/ports').glob('*.sh') if 'rgsx' in p.stem.casefold())
        self.rgsx={'id':'rgsx','name':'RGSX','kind':'rgsx','category':'Jogos','summary':'Central independente. Abre o atalho RGSX existente no Batocera.' if paths else 'RGSX não está instalado neste Batocera. A loja não instala scripts externos automaticamente.','_installed':bool(paths),'script':str(paths[0]) if paths else ''}
        self.filter='Home'; self.focus='content'; self.searching=False
        self.nav_index=0; self.hits=[]; self.nav_hits=[]; self.icon_cache={}
        self.bg=None
        bg=BASE/'assets/space.png'
        if bg.exists(): self.bg=pygame.transform.smoothscale(pygame.image.load(str(bg)).convert(), (1600,900))
        self.view=self.filtered(); self.selected=0
        self.machine=platform.machine()
        try: self.ram=int(Path('/proc/meminfo').read_text().split('MemTotal:')[1].split()[0])//1024
        except (OSError,IndexError,ValueError): self.ram=0
        self.set_filter('Home')

    def filtered(self):
        rows=list(self.apps)
        if self.filter=='RGSX':return [self.rgsx] if hasattr(self,'rgsx') else []
        if self.filter in ('Flatpak','Apps'): rows=[a for a in rows if a['kind']=='flatpak']
        elif self.filter=='Streaming': rows=[a for a in rows if a['kind']=='aura_app']
        elif self.filter=='Instalados': rows=[a for a in rows if a.get('_installed')]
        elif self.filter=='Meu PC': return []
        elif self.filter=='Home' and not self.search:
            wanted=['org.videolan.VLC','com.spotify.Client','org.telegram.desktop','netflix','prime','disney','youtube']
            return [a for key in wanted for a in rows if a.get('appid',a['id'])==key][:7]
        q=self.search.strip().casefold()
        return [a for a in rows if q in (a['name']+' '+a.get('summary','')+' '+a.get('appid','')).casefold()]

    def set_filter(self,f):
        self.filter=f; self.nav_index=self.filters.index(f); self.selected=0; self.detail=False
        self.view=self.filtered()

    def text(self,s,x,y,k='sm',c=TEXT,width=None):
        s=str(s)
        if width:
            while len(s)>1 and self.font[k].size(s)[0]>width: s=s[:-2]+'…'
        self.screen.blit(self.tx(s,k,c),(x,y))

    def panel(self,r,selected=False,purple=False):
        r=pygame.Rect(r)
        if selected:
            for pad,alpha in [(10,12),(6,24),(3,50)]:
                glow=pygame.Surface((r.w+pad*2,r.h+pad*2),pygame.SRCALPHA)
                pygame.draw.rect(glow,((116,66,255) if purple else CYAN)+(alpha,),glow.get_rect(),border_radius=18+pad)
                self.screen.blit(glow,(r.x-pad,r.y-pad))
        layer=pygame.Surface(r.size,pygame.SRCALPHA)
        pygame.draw.rect(layer,(10,25,45,235),layer.get_rect(),border_radius=15)
        pygame.draw.rect(layer,CYAN if selected else (44,68,96),layer.get_rect(),2 if selected else 1,border_radius=15)
        self.screen.blit(layer,r)

    def icon(self,a,x,y,size=66):
        name=a['name']; key=a.get('appid',a['id'])
        file=BASE/'assets/icons'/(key+'.png')
        if key not in self.icon_cache:
            self.icon_cache[key]=pygame.image.load(str(file)).convert_alpha() if file.is_file() else None
        if self.icon_cache[key]:
            img=pygame.transform.smoothscale(self.icon_cache[key],(size,size));self.screen.blit(img,(x,y));return
        colors={'Netflix':(229,9,20),'YouTube':(255,20,40),'Prime Video':(0,178,240),'Disney+':(102,142,255),'VLC':(255,155,35),'Spotify':(29,215,97),'Telegram':(31,170,220)}
        color=colors.get(name,CYAN)
        pygame.draw.rect(self.screen,(*[int(v*.15) for v in color],), (x,y,size,size),border_radius=15)
        if name=='YouTube':
            pygame.draw.rect(self.screen,color,(x+3,y+12,size-6,size-24),border_radius=12)
            pygame.draw.polygon(self.screen,TEXT,[(x+size*.42,y+size*.3),(x+size*.42,y+size*.7),(x+size*.7,y+size*.5)])
        else:
            label={'Netflix':'N','Prime Video':'prime','Disney+':'D+','VLC':'VLC','Spotify':'S','Telegram':'T'}.get(name,''.join(w[0] for w in name.split()[:2]))
            t=self.tx(label,'sm' if len(label)>2 else 'xl',color);self.screen.blit(t,t.get_rect(center=(x+size//2,y+size//2)))

    def nav_icon(self,i,x,y,color):
        s=self.screen
        if i==0:
            pygame.draw.polygon(s,color,[(x,y+10),(x+12,y),(x+24,y+10)])
            pygame.draw.rect(s,color,(x+4,y+9,16,16),border_radius=2)
            pygame.draw.rect(s,(7,21,36),(x+10,y+16,5,9))
        elif i==1:
            for dx in (0,14):
                for dy in (0,14):pygame.draw.rect(s,color,(x+dx,y+dy,10,10),border_radius=2)
        elif i==2:pygame.draw.polygon(s,color,[(x+3,y),(x+24,y+12),(x+3,y+24)])
        elif i==3:
            pygame.draw.rect(s,color,(x,y+4,27,19),border_radius=7)
            pygame.draw.line(s,(7,21,36),(x+5,y+13),(x+12,y+13),2)
            pygame.draw.line(s,(7,21,36),(x+8,y+9),(x+8,y+17),2)
            for dx,dy in ((19,11),(23,15)):pygame.draw.circle(s,(7,21,36),(x+dx,y+dy),2)
        elif i==4:
            pygame.draw.line(s,color,(x+12,y),(x+12,y+16),3)
            pygame.draw.lines(s,color,False,[(x+6,y+10),(x+12,y+17),(x+18,y+10)],3)
            pygame.draw.lines(s,color,False,[(x+1,y+18),(x+1,y+24),(x+24,y+24),(x+24,y+18)],2)
        else:
            pygame.draw.rect(s,color,(x,y,26,18),2,border_radius=2)
            pygame.draw.line(s,color,(x+13,y+18),(x+13,y+24),2)
            pygame.draw.line(s,color,(x+6,y+24),(x+20,y+24),2)

    def grid_metrics(self): return 3,2,20,318,200,396,250
    def page(self): return self.selected//6,6
    def cardrect(self,si):
        return pygame.Rect(318+(si%3)*416,200+(si//3)*270,396,250)
    def home_rect(self,i):
        return pygame.Rect(318+i*416,198,396,226) if i<3 else pygame.Rect(318+(i-3)*312,506,292,214)

    def draw_card_at(self,a,r,index,compact=False):
        sel=self.focus=='content' and index==self.selected and not self.detail and not self.job
        self.panel(r,sel); size=62 if compact else 72
        self.icon(a,r.centerx-size//2,r.y+20,size)
        self.text(a['name'],r.x+22,r.y+size+31,'md',width=r.w-44)
        desc={'VLC':'Reprodutor de mídia','Spotify':'Música e podcasts','Telegram':'Mensagens','Netflix':'Filmes e séries','Prime Video':'Filmes e séries','Disney+':'Filmes e séries','YouTube':'Vídeos e música'}.get(a['name'],a.get('category','Aplicativo'))
        self.text(desc,r.x+22,r.y+size+65,'xs',MUTED,width=r.w-44)
        btn=pygame.Rect(r.x+20,r.bottom-51,r.w-40,34)
        pygame.draw.rect(self.screen,(12,73,111) if sel else (24,43,76),btn,border_radius=10)
        pygame.draw.rect(self.screen,CYAN if sel else (55,84,129),btn,1,border_radius=10)
        action='Abrir' if a.get('_installed') else 'Não instalado' if a['kind']=='rgsx' else 'Configurar' if a['kind']=='aura_app' else 'Instalar'
        t=self.tx(action,'sm');self.screen.blit(t,t.get_rect(center=btn.center));self.hits.append((r,index))

    def draw_main(self):
        self.screen.fill((3,10,19))
        if self.bg:self.screen.blit(self.bg,(0,0))
        veil=pygame.Surface((1600,900),pygame.SRCALPHA);veil.fill((1,8,20,135));self.screen.blit(veil,(0,0))
        side=pygame.Surface((278,900),pygame.SRCALPHA);side.fill((3,12,23,238));self.screen.blit(side,(0,0))
        pygame.draw.line(self.screen,(28,52,76),(278,0),(278,900))
        pygame.draw.polygon(self.screen,CYAN,[(28,51),(43,25),(57,51),(43,77)])
        pygame.draw.polygon(self.screen,(40,96,245),[(46,51),(61,25),(75,51),(61,77)])
        self.text('BATOCERA',91,27,'md')
        self.text('STORE  /  A U R A',93,62,'xs',MUTED)
        self.nav_hits=[]
        for i,label in enumerate(self.filters):
            r=pygame.Rect(20,120+i*69,238,54);active=self.filter==label
            if active:self.panel(r,self.focus=='nav')
            self.nav_icon(i,39,r.y+14,CYAN if active else MUTED)
            self.text(label,89,r.y+14,'sm',TEXT if active else MUTED)
            self.nav_hits.append((r,label))
        self.panel((20,620,238,163));self.text('SEU BATOCERA',39,640,'xs',CYAN)
        self.text(self.machine or 'Sistema',39,674,'md')
        self.text(f'{self.ram/1024:.1f} GB de RAM' if self.ram else 'Memória não consultada',39,715,'xs',MUTED)
        self.text(f'{len(self.inst)} apps Flatpak',39,748,'xs',MUTED)
        self.search_rect=pygame.Rect(318,28,740,48);self.panel(self.search_rect,self.searching)
        self.text(self.search or 'Pesquisar aplicativos, jogos e mais…',340,41,'sm',TEXT if self.search else MUTED,690)
        self.text(time.strftime('%H:%M'),1460,34,'lg')
        self.text('BIBLIOTECA AURA',1140,44,'xs',CYAN)
        self.hits=[]
        home=self.filter=='Home' and not self.search
        if home:
            self.text('Flathub Apps',318,107,'lg');self.text('Aplicativos Linux para o seu Batocera.',318,151,'sm',MUTED)
            self.text('Streaming via Chrome',318,447,'lg');self.text('Seus filmes, séries e música em um só lugar.',318,483,'xs',MUTED)
            for i,a in enumerate(self.view): self.draw_card_at(a,self.home_rect(i),i,i>=3)
            self.rgsx_rect=pygame.Rect(318,755,1228,82)
            self.panel(self.rgsx_rect,False,True);self.text('RGSX',344,769,'lg',(175,121,255))
            self.text('Central de jogos independente',490,776,'sm')
            self.text('Disponível na categoria RGSX' if self.rgsx['_installed'] else 'Nenhum atalho RGSX encontrado neste Batocera',490,806,'xs',MUTED)
            self.text('ABRIR CATEGORIA  >',1293,789,'xs',CYAN)
        elif self.filter=='Meu PC':
            self.text('Seu PC',318,121,'xl');self.panel((318,218,1228,390))
            for i,line in enumerate([f'Arquitetura: {self.machine}',f'Memória disponível ao sistema: {self.ram} MB',f'Aplicativos Flatpak instalados: {len(self.inst)}','A reprodução de streaming depende do navegador, DRM e serviço.','Conexão e instalações são verificadas ao executar cada ação.']):
                self.text(line,351,252+i*60,'md' if i<3 else 'sm',TEXT if i<3 else MUTED)
        else:
            self.text('Resultados da busca' if self.search else self.filter,318,117,'lg')
            pg,per=self.page();start=pg*per
            self.text(f'{len(self.view)} aplicativos  ·  Página {pg+1}/{max(1,(len(self.view)+per-1)//per)}',318,163,'xs',MUTED)
            for si,a in enumerate(self.view[start:start+per]):self.draw_card_at(a,self.cardrect(si),start+si)
            if not self.view:self.text('Nenhum aplicativo encontrado.',340,262,'md',MUTED)
        pygame.draw.rect(self.screen,(4,13,25),(0,858,1600,42));pygame.draw.line(self.screen,(32,63,88),(0,858),(1600,858))
        for x,key,label,color in [(34,'A','Selecionar',GREEN),(260,'B','Voltar',(255,66,83)),(440,'X','Instalar / abrir',(58,133,255)),(747,'Y','Detalhes',(255,208,59))]:
            pygame.draw.circle(self.screen,color,(x+13,880),13);t=self.tx(key,'xs',(3,10,20));self.screen.blit(t,t.get_rect(center=(x+13,880)));self.text(label,x+36,869,'xs',MUTED)
        self.text('TAB  categorias    /  buscar',1195,869,'xs',MUTED)
        self.draw_notice()

    def move(self,dx,dy):
        if self.detail or self.job:return
        if self.focus=='nav':
            if dx>0:self.focus='content'
            elif dy:self.set_filter(self.filters[(self.nav_index+dy)%len(self.filters)])
            return
        if not self.view:
            self.focus='nav';return
        if self.filter=='Home' and not self.search:
            i=self.selected
            if dx<0 and i in (0,3):self.focus='nav';return
            if dy>0 and i<3:i=3+min(3,round(i*1.5))
            elif dy<0 and i>=3:i=min(2,round((i-3)/1.5))
            elif dx:i=max(0 if i<3 else 3,min(2 if i<3 else len(self.view)-1,i+dx))
            self.selected=max(0,min(len(self.view)-1,i))
        else:
            if dx<0 and self.selected%3==0:self.focus='nav';return
            super().move(dx,dy)

    def next_filter(self):self.set_filter(self.filters[(self.nav_index+1)%len(self.filters)])
    def start_action(self):
        if self.view and self.view[self.selected]['kind']=='rgsx':
            path=self.view[self.selected].get('script','')
            if not path or not Path(path).is_file():self.notify('RGSX não instalado. Nenhuma alteração foi feita.',7);return
            pygame.quit();os.execvp('bash',['bash',path])
        else:super().start_action()
    def draw_detail(self):
        super().draw_detail()
        if self.view and self.view[self.selected]['kind']=='rgsx':
            btn=self.action_rect
            pygame.draw.rect(self.screen,(31,40,74),btn,border_radius=12)
            t=self.tx('A · ABRIR' if self.rgsx['_installed'] else 'NÃO INSTALADO','md',TEXT if self.rgsx['_installed'] else MUTED)
            self.screen.blit(t,t.get_rect(center=btn.center))
    def handle_button(self,b):
        if self.job:
            if b==1 and self.worker:self.worker.cancel()
            return True
        if b==1:
            if self.detail:self.detail=False
            elif self.searching:self.searching=False
            elif self.focus=='content':self.focus='nav'
            else:return False
        elif b==0:
            if self.focus=='nav':self.focus='content'
            elif self.view:
                if self.detail:self.start_action()
                else:self.detail=True
        elif b==2 and self.view and self.focus=='content':self.detail=True;self.start_action()
        elif b==3 and self.view:self.detail=True
        return True

    def loop(self):
        running=True;pygame.key.set_repeat(330,100)
        while running:
            self.jobs()
            for e in pygame.event.get():
                if e.type==pygame.QUIT:running=False
                elif e.type in (pygame.JOYDEVICEADDED,pygame.JOYDEVICEREMOVED):self.scan_joys()
                elif e.type==pygame.JOYBUTTONDOWN:
                    if self.handle_button(e.button) is False:running=False
                elif e.type==pygame.JOYHATMOTION and not self.job:self.move(e.value[0],-e.value[1])
                elif e.type==pygame.JOYAXISMOTION and time.monotonic()-self.axis_ts>.22 and not self.job:
                    if e.axis in (0,1) and abs(e.value)>.65:
                        self.move((1 if e.value>0 else -1) if e.axis==0 else 0,(1 if e.value>0 else -1) if e.axis==1 else 0);self.axis_ts=time.monotonic()
                elif e.type==pygame.KEYDOWN:
                    if self.searching:
                        if e.key in (pygame.K_ESCAPE,pygame.K_RETURN):self.searching=False
                        elif e.key==pygame.K_BACKSPACE:self.search=self.search[:-1]
                        elif e.key==pygame.K_DELETE:self.search=''
                        elif e.unicode.isprintable() and len(self.search)<64:self.search+=e.unicode
                        self.view=self.filtered();self.selected=0;continue
                    if e.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                        if self.handle_button(1) is False:running=False
                    elif e.key==pygame.K_RETURN:self.handle_button(0)
                    elif e.key==pygame.K_x:self.handle_button(2)
                    elif e.key==pygame.K_y:self.handle_button(3)
                    elif not self.job and not self.detail:
                        if e.key in (pygame.K_SLASH,pygame.K_F3):self.searching=True
                        elif e.key==pygame.K_TAB:self.next_filter()
                        elif e.key==pygame.K_LEFT:self.move(-1,0)
                        elif e.key==pygame.K_RIGHT:self.move(1,0)
                        elif e.key==pygame.K_UP:self.move(0,-1)
                        elif e.key==pygame.K_DOWN:self.move(0,1)
                elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and not self.job:
                    dw,dh=self.display.get_size();pos=(e.pos[0]*1600/dw,e.pos[1]*900/dh)
                    if self.detail:
                        if getattr(self,'action_rect',pygame.Rect(0,0,0,0)).collidepoint(pos):self.start_action()
                    elif self.search_rect.collidepoint(pos):self.searching=True
                    elif self.filter=='Home' and getattr(self,'rgsx_rect',pygame.Rect(0,0,0,0)).collidepoint(pos):self.set_filter('RGSX');self.focus='content'
                    else:
                        self.searching=False
                        for r,label in self.nav_hits:
                            if r.collidepoint(pos):self.set_filter(label);self.focus='nav';break
                        for r,i in self.hits:
                            if r.collidepoint(pos):self.selected=i;self.focus='content';self.detail=True;break
            if self.job:self.draw_progress()
            elif self.detail and self.view:self.draw_detail()
            else:self.draw_main()
            pygame.transform.smoothscale(self.screen,self.display.get_size(),self.display)
            pygame.display.flip();self.clock.tick(30)
        pygame.quit()

if __name__=='__main__':NeonStore().loop()
