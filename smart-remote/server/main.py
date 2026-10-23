import argparse
import asyncio
import contextlib
import fcntl
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import ssl
import time
from aiohttp import web, WSMsgType
from auth import Auth
from inputs import Inputs
import apps
import network_config

ROOT=Path(__file__).resolve().parents[1]
COOKIE='bsr_session'


class Remote:
    def __init__(self, config, inputs, auth_store=None):
        self.config=config;self.inputs=inputs;self.auth=Auth(store=auth_store)
        self.active=None;self.active_id=None;self.last_input=0;self.last_app=0
        self.paused=False
        self.ws_gate=asyncio.Lock()
        self.launcher=apps.Launcher();self.app_task=None
        self.allowed=[ipaddress.ip_network(s) for s in config['networks']]
        self.origins=set(config['origins'])
        self.log=logging.getLogger('remote')

    @web.middleware
    async def guard(self, request, handler):
        try:
            address=ipaddress.ip_address(request.remote)
            if not any(address in net for net in self.allowed):raise web.HTTPForbidden()
            origin=f'{request.scheme}://{request.host}'
            if origin not in self.origins:raise web.HTTPForbidden(text='Host não autorizado.')
            if request.method!='GET' or request.path=='/ws':
                if request.headers.get('Origin') not in self.origins or request.headers.get('Origin')!=origin:
                    raise web.HTTPForbidden(text='Origem inválida.')
            response=await handler(request)
            if not isinstance(response,web.WebSocketResponse):
                response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",'Referrer-Policy':'no-referrer'})
            return response
        except ValueError as e:return web.json_response({'error':str(e)},status=400)

    def session(self,r):
        try:return self.auth.session(r.cookies.get(COOKIE,''))
        except ValueError:raise web.HTTPUnauthorized(text='Sessão inválida.')

    async def pair(self,r):
        data=await r.json()
        if not isinstance(data,dict) or not isinstance(data.get('pin'),str) or len(data['pin'])!=6:raise ValueError('PIN inválido.')
        name=data.get('name','Celular')
        if not isinstance(name,str):raise ValueError('Nome inválido.')
        try:token=self.auth.request(data['pin'],r.remote,name)
        except ValueError:
            self.log.info('pair rejected');raise
        # The user explicitly chose PIN-only authorization. PIN still opens locally,
        # expires in 300s, has attempt limits and is consumed once.
        self.auth.approve(self.auth.digest(token))
        token=self.auth.exchange(token)
        self.log.info('pair authorized by local PIN')
        response=web.json_response({'approved':True})
        response.set_cookie(COOKIE,token,httponly=True,samesite='Strict',secure=r.secure,max_age=self.auth.DEVICE_TTL)
        return response

    async def pair_status(self,r):
        token=self.auth.exchange(r.cookies.get('bsr_pending',''))
        response=web.json_response({'approved':bool(token)})
        if token:
            response.del_cookie('bsr_pending',path='/api/pair-status')
            response.set_cookie(COOKIE,token,httponly=True,samesite='Strict',secure=r.secure,max_age=self.auth.DEVICE_TTL)
        return response

    async def state(self,r):
        row=self.session(r)
        self.auth.remember(row)
        response=web.json_response({'v':1,'csrf':row['csrf'],'busy':self.active is not None, 'apps':list(await apps.catalog()),'text':bool(__import__('shutil').which('xdotool')),'fake':self.inputs.fake})
        response.set_cookie(COOKIE,r.cookies[COOKIE],httponly=True,samesite='Strict',secure=r.secure,max_age=self.auth.DEVICE_TTL)
        return response

    async def logout(self,r):
        row=self.session(r)
        if r.headers.get('X-CSRF-Token')!=row['csrf']:raise web.HTTPForbidden()
        ident=self.auth.digest(r.cookies[COOKIE]);await self.revoke(ident)
        response=web.json_response({'ok':True});response.del_cookie(COOKIE);return response

    async def revoke(self,ident=None):
        self.auth.revoke(ident)
        if self.active is not None and (ident is None or ident==self.active_id):
            self.inputs.release();await self.active.close(code=4001,message=b'Revoked')

    async def websocket(self,r):
        row=self.session(r)
        async with self.ws_gate:
            if self.active is not None:raise web.HTTPConflict(text='Outro controlador está ativo.')
            ws=web.WebSocketResponse(max_msg_size=4096,heartbeat=5)
            await ws.prepare(r)
            self.active=ws;self.active_id=self.auth.digest(r.cookies[COOKIE])
        seq=0;bucket=300;refill=time.monotonic();self.last_input=refill
        try:
            first=await ws.receive_json(timeout=5)
            if first!={'type':'hello','v':1,'csrf':row['csrf']}:
                await ws.close(code=4003);return ws
            await ws.send_json({'type':'ready','v':1})
            self.log.info('controller connected')
            async for msg in ws:
                if msg.type!=WSMsgType.TEXT:break
                try:
                    self.session(r)
                    m=json.loads(msg.data)
                    if not isinstance(m,dict):raise ValueError('Objeto esperado.')
                    now=time.monotonic();bucket=min(300,bucket+(now-refill)*180);refill=now
                    if bucket<1:raise ValueError('Limite de eventos excedido.')
                    bucket-=1
                    if m.get('v')!=1 or type(m.get('seq'))!=int or m['seq']<=seq:raise ValueError('Versão ou sequência inválida.')
                    seq=m['seq'];self.last_input=now
                    if m.get('type')=='ping':await ws.send_json({'type':'pong','seq':seq});continue
                    if self.paused and m.get('type') not in ('release_all','mode'):
                        await ws.send_json({'type':'error','message':'Feche o painel local na TV para controlar.'});continue
                    if m.get('type') in ('launch_app','home'):
                        if m['type']=='launch_app' and self.inputs.mode!='apps':raise ValueError('Ative Apps.')
                        if self.app_task is not None and not self.app_task.done():
                            await ws.send_json({'type':'app_result','ok':False,'message':'Aguarde a operação atual.'})
                            continue
                        self.inputs.release()
                        self.app_task=asyncio.create_task(self.app_action(ws,m))
                    else:await self.inputs.command(m)
                    await ws.send_json({'type':'ack','seq':seq})
                except (ValueError,TypeError,KeyError,web.HTTPException) as e:
                    self.inputs.release()
                    await ws.send_json({'type':'error','message':str(e)[:160]})
                    await ws.close(code=4002);break
        except (TimeoutError,ValueError,ConnectionError):pass
        finally:
            self.inputs.release();self.active=None;self.active_id=None
            self.log.info('controller disconnected; inputs released')
        return ws

    async def app_action(self,ws,m):
        try:
            message=await (self.launcher.home() if m['type']=='home' else self.launcher.launch(m.get('app')))
            result={'type':'app_result','ok':True,'message':message}
        except (ValueError,TypeError) as e:
            result={'type':'app_result','ok':False,'message':str(e)[:180]}
        except Exception:
            self.log.exception('Application action failed')
            result={'type':'app_result','ok':False,'message':'Falha ao consultar o Batocera. Tente Home antes de abrir outro app.'}
        if not ws.closed:
            with contextlib.suppress(ConnectionError):await ws.send_json(result)

    async def watchdog(self):
        while True:
            await asyncio.sleep(.25)
            if self.active is not None and time.monotonic()-self.last_input>2.5:
                self.inputs.release();await self.active.close(code=4000,message=b'Input timeout')

    async def admin(self,reader,writer):
        try:
            m=json.loads(await asyncio.wait_for(reader.readline(),3));action=m.get('action')
            if action=='open':result={'pin':self.auth.open_pairing(),'url':self.config['origins'][0]+'/pair','expires':self.auth.PIN_TTL}
            elif action=='approve':self.auth.approve(m['id']);result={'ok':True}
            elif action=='revoke':await self.revoke(m.get('id'));result={'ok':True}
            elif action=='pause':
                self.paused=bool(m.get('enabled',True));self.inputs.release();result={'ok':True}
            elif action=='status':
                now=self.auth.clock()
                result={'active':self.active_id,'pending':[{**v,'id':k} for k,v in self.auth.pending.items() if v['until']>now],
                        'sessions':[{k:v for k,v in row.items() if k!='csrf'}|{'id':ident} for ident,row in self.auth.sessions.items()]}
            else:raise ValueError('Ação inválida.')
            writer.write((json.dumps(result)+'\n').encode());await writer.drain()
        except (ValueError,KeyError,TimeoutError):writer.write(b'{"error":"Invalid local request"}\n')
        finally:writer.close();await writer.wait_closed()

    def app(self):
        app=web.Application(middlewares=[self.guard],client_max_size=4096)
        app.router.add_post('/api/pair',self.pair);app.router.add_post('/api/pair-status',self.pair_status)
        app.router.add_get('/api/state',self.state);app.router.add_post('/api/logout',self.logout)
        app.router.add_get('/ws',self.websocket)
        async def index(r):return web.FileResponse(ROOT/'client/index.html')
        async def control(r):
            try:self.session(r)
            except (web.HTTPUnauthorized,ValueError):raise web.HTTPFound('/pair')
            return web.FileResponse(ROOT/'client/control.html')
        app.router.add_get('/',index);app.router.add_get('/pair',index)
        app.router.add_get('/control',control)
        # Explicit public asset allowlist, never the project/config directory.
        for name in ('app.js','gamepad-editor.js','pair.js','styles.css','assets/rgsx-logo.png','install-home.js','manifest.webmanifest','assets/nexora-180.png','assets/nexora-192.png','assets/nexora-512.png'):
            async def file(r,n=name):return web.FileResponse(ROOT/'client'/n)
            app.router.add_get('/'+name,file)
        return app


async def run(config,fake=False):
    runtime=ROOT/'run';runtime.mkdir(mode=0o700,exist_ok=True);os.chmod(runtime,0o700)
    lock=open(runtime/'lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (runtime/'pid').write_text(str(os.getpid())+'\n')
    deadzone=config.get('analog_deadzone',0.12)
    if type(deadzone) not in (int,float) or not 0<=deadzone<=0.4:raise ValueError('analog_deadzone deve estar entre 0 e 0.4')
    backend=Inputs(fake)
    backend.deadzone=deadzone
    remote=Remote(config,backend,ROOT/'state/devices.json')
    socket=runtime/'admin.sock';socket.unlink(missing_ok=True)
    runner=web.AppRunner(remote.app(),access_log=None);await runner.setup()
    tls=None
    if config.get('cert'):
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(config['cert'],config['key'])
    await web.TCPSite(runner,config['bind'],config.get('port',8765),ssl_context=tls).start()
    admin=await asyncio.start_unix_server(remote.admin,path=str(socket));os.chmod(socket,0o600)
    task=asyncio.create_task(remote.watchdog());stop=asyncio.Event()
    for sig in (signal.SIGTERM,signal.SIGINT):asyncio.get_running_loop().add_signal_handler(sig,stop.set)
    remote.log.info('service started; pairing closed')
    try:await stop.wait()
    finally:
        backend.release()
        if remote.active is not None:await remote.active.close(code=1001,message=b'Service restarting')
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):await task
        admin.close();await admin.wait_closed();await runner.cleanup();backend.close()
        socket.unlink(missing_ok=True);(runtime/'pid').unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fake',action='store_true');args=parser.parse_args()
    config=json.loads((ROOT/'config.json').read_text())
    if args.fake and config['bind'] not in ('127.0.0.1','::1'):raise SystemExit('Fake backend only on loopback.')
    if not args.fake:config=network_config.current(config)
    (ROOT/'logs').mkdir(exist_ok=True)
    handler=RotatingFileHandler(ROOT/'logs/server.log',maxBytes=500000,backupCount=2)
    logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(message)s')
    asyncio.run(run(config,args.fake))
