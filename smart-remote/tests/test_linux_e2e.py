"""Run only in Batocera: observes real evdev devices, not the fake adapter."""
import asyncio
import json
import socket
import sys
import time
from pathlib import Path
import aiohttp
from evdev import InputDevice,list_devices
BASE=Path('/userdata/system/batocera-smart-remote')

def admin(action,**kw):
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(str(BASE/'run/admin.sock'));s.sendall((json.dumps({'action':action,**kw})+'\n').encode())
        return json.loads(s.makefile().readline())

async def run():
    url=admin('open')['url'].removesuffix('/pair')
    devices=[InputDevice(p) for p in list_devices()]
    pad=next(d for d in devices if d.name=='Batocera Smart Remote Gamepad')
    keyboard=next(d for d in devices if d.name=='Batocera Smart Remote Keyboard')
    events=[]
    async def read(dev):
        async for event in dev.async_read_loop():events.append((dev.name,event.type,event.code,event.value))
    readers=[asyncio.create_task(read(d)) for d in (pad,keyboard)]
    admin('revoke');pair=admin('open')
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),headers={'Origin':url}) as c:
        async with c.post(url+'/api/pair',json={'pin':pair['pin']}) as r:assert r.status==200
        async with c.get(url+'/api/state') as r:csrf=(await r.json())['csrf']
        async with c.ws_connect(url+'/ws') as ws:
            await ws.send_json({'v':1,'type':'hello','csrf':csrf});assert (await ws.receive_json())['type']=='ready'
            seq=0;latencies=[]
            async def send(**m):
                nonlocal seq
                seq+=1;t=time.perf_counter();await ws.send_json({'v':1,'seq':seq,**m});r=await ws.receive_json();assert r['type'] in ('ack','pong'),r;latencies.append((time.perf_counter()-t)*1000)
            await send(type='mode',mode='gamepad')
            await send(type='button',control='A',phase='down');await send(type='button',control='L1',phase='down');await send(type='button',control='L3',phase='down');await send(type='button',control='R3',phase='down')
            await send(type='axis',stick='LEFT',x=.75,y=-.5);await asyncio.sleep(.1)
            assert set((304,310,317,318)).issubset(set(pad.active_keys()))
            assert pad.absinfo(0).value>20000 and pad.absinfo(1).value<0
            await send(type='release_all');await asyncio.sleep(.1);assert not pad.active_keys();assert pad.absinfo(0).value==0
            for name,code in [('A',304),('B',305),('X',307),('Y',308),('L1',310),('R1',311),('SELECT_GAME',314),('START',315),('L3',317),('R3',318)]:
                await send(type='button',control=name,phase='down');await asyncio.sleep(.02);assert code in pad.active_keys(),name
                await send(type='button',control=name,phase='up')
            for name,axis in [('L2',2),('R2',5)]:
                await send(type='button',control=name,phase='down');await asyncio.sleep(.02);assert pad.absinfo(axis).value==255,name
                await send(type='button',control=name,phase='up')
            for name,axis,value in [('GP_UP',17,-1),('GP_DOWN',17,1),('GP_LEFT',16,-1),('GP_RIGHT',16,1)]:
                await send(type='button',control=name,phase='down');await asyncio.sleep(.02);assert pad.absinfo(axis).value==value,name
                await send(type='button',control=name,phase='up')
            await send(type='axis',stick='LEFT',x=.6,y=-.4);await send(type='axis',stick='RIGHT',x=-.7,y=.5);await asyncio.sleep(.02)
            assert pad.absinfo(0).value>0 and pad.absinfo(1).value<0 and pad.absinfo(3).value<0 and pad.absinfo(4).value>0
            await send(type='release_all')
            await send(type='mode',mode='remote')
            for name,code in [('UP',103),('DOWN',108),('LEFT',105),('RIGHT',106),('SELECT',28),('BACK',1),('MENU',57),('VOLUME_UP',115),('VOLUME_DOWN',114),('PLAY_PAUSE',164)]:
                await send(type='button',control=name,phase='down');await asyncio.sleep(.02);assert code in keyboard.active_keys(),name
                await send(type='button',control=name,phase='up')

            await send(type='mode',mode='mouse');await send(type='mouse_move',dx=40,dy=20)
            await send(type='button',control='MOUSE_LEFT',phase='down');await send(type='button',control='MOUSE_LEFT',phase='up')
            await send(type='button',control='SCROLL_DOWN',phase='down');await send(type='button',control='SCROLL_DOWN',phase='up')
            await send(type='mode',mode='remote');await send(type='button',control='RIGHT',phase='down')
            # Actual websocket close must release the physical virtual device.
        await asyncio.sleep(.3);assert not keyboard.active_keys();assert not pad.active_keys()
        assert any(e[1:]==(2,0,40) for e in events)
        assert any(e[1:]==(2,8,-1) for e in events)
        # Explicitly test watchdog on a connection that stops sending application heartbeats.
        async with c.ws_connect(url+'/ws') as ws:
            await ws.send_json({'v':1,'type':'hello','csrf':csrf});await ws.receive_json()
            await ws.send_json({'v':1,'seq':1,'type':'button','control':'LEFT','phase':'down'});await ws.receive_json()
            await asyncio.sleep(3.2);assert not keyboard.active_keys()
        admin('revoke')
        async with c.get(url+'/api/state') as r:assert r.status==401
    for task in readers:task.cancel()
    await asyncio.gather(*readers,return_exceptions=True)
    for device in devices:device.close()
    latencies.sort()
    print(json.dumps({'environment':'Batocera43.1 QEMU Linux real uinput; not physical hardware','result':'PASS','evdev_events':len(events),'all_buttons_and_both_sticks':True,'simultaneous_buttons':True,'axes':True,'mouse_wheel':True,'disconnect_release':True,'watchdog_release':True,'revoke':True,'ack_loopback_ms_p50':latencies[len(latencies)//2],'ack_loopback_ms_p95':latencies[int(len(latencies)*.95)]},indent=2))

if __name__=='__main__':asyncio.run(run())
