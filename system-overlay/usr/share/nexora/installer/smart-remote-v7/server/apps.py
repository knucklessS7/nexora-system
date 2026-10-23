"""Only fixed, installed shortcuts already registered in EmulationStation."""
from pathlib import Path
import aiohttp
import asyncio
import json
import os

PATHS = {
 'YouTube':['apps/YouTube.app'], 'Disney':['apps/Disney+.app','apps/Disney.app'],
 'Netflix':['apps/Netflix.app'], 'Prime Video':['apps/Prime Video.app'],
 'Loja':['apps/Batocera Store.app','ports/Batocera Store.sh'],
 'RGSX':['ports/RGSX/RGSX.sh','ports/RGSX.sh','apps/RGSX.app']}

async def catalog():
    registered=set()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as s:
            for system in ('apps','ports'):
                async with s.get('http://127.0.0.1:1234/systems/'+system+'/games') as r:
                    if r.status==200:
                        rows=await r.json(content_type=None)
                        registered.update(row['path'] for row in rows)
    except (aiohttp.ClientError, ValueError, TimeoutError):pass
    result={}
    for name,paths in PATHS.items():
        for rel in paths:
            p=Path('/userdata/roms')/rel
            if p.is_file() and str(p) in registered:
                if name in ('YouTube','Disney','Netflix','Prime Video') and not Path('/userdata/system/aura/streaming-native-v4/launch.sh').exists():continue
                result[name]=str(p);break
    return result

class AppError(ValueError):
    """Recoverable launch/state error; keep the controller connected."""


class Launcher:
    def __init__(self, base='http://127.0.0.1:1234'):
        self.base=base
        self.lock=asyncio.Lock()
        self.uncertain=False

    async def request(self, session, route, path=None):
        try:
            async with session.request('POST' if path else 'GET',self.base+route,
                    data=path.encode() if path else None,
                    headers={'Content-Type':'text/plain'}) as r:
                body=await r.text()
                if r.status not in (200,201):raise AppError('Batocera não confirmou a operação.')
                return r.status,body
        except (aiohttp.ClientError,TimeoutError) as e:
            raise AppError('Batocera não respondeu. Nenhum segundo app será aberto.') from e

    async def running(self,s):
        status,body=await self.request(s,'/runningGame')
        if status==201 and json.loads(body).get('msg')=='NO GAME RUNNING':return False
        if status==200 and isinstance(json.loads(body),dict):return True
        raise AppError('Não foi possível confirmar o aplicativo ativo.')

    async def launch(self,name):
        if self.lock.locked():raise AppError('Aguarde a operação atual.')
        async with self.lock:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as s:
                if self.uncertain or await self.running(s):
                    raise AppError('Já existe um app aberto ou iniciando. Use Home antes de abrir outro.')
                path=(await catalog()).get(name)
                if not path:raise AppError('Aplicativo ausente ou não configurado no EmulationStation.')
                status,body=await self.request(s,'/isIdle')
                if status!=200 or json.loads(body)!=[True]:raise AppError('Batocera está ocupado. Aguarde antes de abrir um app.')
                # Reserve before POST: even an ambiguous timeout must not allow a second launch.
                self.uncertain=True
                await self.request(s,'/launch',path)
                for _ in range(60):
                    if await self.running(s):
                        self.uncertain=False
                        return 'Aplicativo aberto. Use Home para voltar ao Batocera.'
                    await asyncio.sleep(.25)
                raise AppError('Abertura ainda não confirmada. Use Home antes de tentar novamente.')

    async def close_app_window(self):
        async def xdo(*args):
            try:
                proc=await asyncio.create_subprocess_exec('xdotool',*args,
                    env={**os.environ,'DISPLAY':os.environ.get('DISPLAY',':0')},
                    stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
                out,_=await asyncio.wait_for(proc.communicate(),3)
            except FileNotFoundError:raise AppError('Feche o app pela TV: xdotool não está disponível.')
            except TimeoutError:
                proc.kill();await proc.wait();raise AppError('A janela não respondeu ao Home.')
            if proc.returncode:raise AppError('Não foi possível identificar/fechar a janela. Feche o app pela TV.')
            return out.decode().strip()
        window=await xdo('getactivewindow')
        if not window.isdecimal():raise AppError('Janela ativa não identificada.')
        window_pid=int(await xdo('getwindowpid',window))
        # Flatpak may publish a PID from its namespace. Match NSpid and require
        # ancestry under ES; do not accept arbitrary host processes with that PID.
        candidates={window_pid}
        for process in Path('/proc').iterdir():
            if not process.name.isdecimal():continue
            try:
                lines=(process/'status').read_text().splitlines()
                ns=next((line.split()[1:] for line in lines if line.startswith('NSpid:')),[])
                if ns and int(ns[-1])==window_pid:candidates.add(int(process.name))
            except (OSError,ValueError):continue
        # Close only a window owned by a descendant of ES, never the ES window itself.
        owned=False
        for candidate in candidates:
            pid=candidate
            for _ in range(50):
                try:
                    status=(Path('/proc')/str(pid)/'status').read_text()
                    pid=int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
                    if pid<=1:break
                    exe=(Path('/proc')/str(pid)/'exe').resolve(strict=True)
                except (OSError,ValueError,StopIteration):break
                if exe.name=='emulationstation':owned=True;break
            if owned:break
        if not owned:raise AppError('A janela em foco não pertence ao app do Batocera. Volte à janela do app e tente Home.')
        # WM_DELETE_WINDOW: graceful request; no global kill and no injected keystrokes.
        await xdo('windowquit',window)

    async def home(self):
        if self.lock.locked():raise AppError('Aguarde a abertura terminar antes de voltar ao início.')
        async with self.lock:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as s:
                if await self.running(s):
                    _,body=await self.request(s,'/runningGame')
                    if str(json.loads(body).get('path','')).endswith('.app'):
                        await self.close_app_window()
                    else:
                        await self.request(s,'/emukill')
                    for _ in range(60):
                        if not await self.running(s):break
                        await asyncio.sleep(.25)
                    else:raise AppError('O app ainda está fechando. Aguarde; outro app continua bloqueado.')
                # Allow ES to restore its window and second row before admitting a new launch.
                await asyncio.sleep(.75)
                if await self.running(s):raise AppError('O app ainda está ativo. Feche pela TV e tente novamente.')
                await self.request(s,'/aura/home')
                self.uncertain=False
                return 'Você voltou ao Batocera.'
