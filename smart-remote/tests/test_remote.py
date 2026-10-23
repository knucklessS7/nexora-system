import asyncio
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from aiohttp import web,ClientSession,CookieJar,WSServerHandshakeError
from auth import Auth
from inputs import Inputs
from main import Remote

class AuthTests(unittest.TestCase):
    def test_pair_expiry_limit_revoke(self):
        now=[1.0];a=Auth(lambda:now[0])
        with self.assertRaises(ValueError):a.request('123456','ip','test')
        pin=a.open_pairing();now[0]+=301
        with self.assertRaises(ValueError):a.request(pin,'ip','test')
        pin=a.open_pairing()
        for _ in range(5):
            with self.assertRaises(ValueError):a.request('bad','other','test')
        with self.assertRaises(ValueError):a.request(pin,'other','test')
        pending=a.request(pin,'new','test');self.assertIsNone(a.exchange(pending))
        a.approve(a.digest(pending));token=a.exchange(pending);a.session(token)
        a.sessions.clear()
        with self.assertRaises(ValueError):a.session(token)

class InputsTests(unittest.IsolatedAsyncioTestCase):
    async def test_simultaneous_axes_release(self):
        b=Inputs(True);await b.command({'type':'mode','mode':'gamepad'})
        for _ in range(300):
            b.button('A','down');b.button('L1','down');b.axis('LEFT',.8,-.5)
            self.assertEqual(b.held,{'A','L1'});b.release();self.assertFalse(b.held)
        for x in (float('nan'),2,None):
            with self.assertRaises(ValueError):b.axis('LEFT',x,0)
        with self.assertRaises(ValueError):b.button('HOME','down')
        await b.command({'type':'mode','mode':'mouse'})
        await b.command({'type':'mouse_move','dx':4,'dy':-2})
        with self.assertRaises(ValueError):await b.command({'type':'type_text','text':'abc\n'})

class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend=Inputs(True)
        self.r=Remote({'origins':[],'networks':['127.0.0.0/8']},self.backend)
        self.runner=web.AppRunner(self.r.app());await self.runner.setup()
        site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
        self.url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]);self.r.origins.add(self.url)
        self.c=ClientSession(cookie_jar=CookieJar(unsafe=True),headers={'Origin':self.url})
    async def asyncTearDown(self):
        if self.r.active:await self.r.active.close()
        await self.c.close();await self.runner.cleanup()
    async def login(self):
        pin=self.r.auth.open_pairing()
        async with self.c.post(self.url+'/api/pair',json={'pin':pin}) as res:self.assertEqual(res.status,200)
        self.assertFalse(self.r.auth.pending)
        self.assertEqual(len(self.r.auth.sessions),1)
        async with self.c.post(self.url+'/api/pair',json={'pin':pin}) as res:self.assertEqual(res.status,400)
        async with self.c.get(self.url+'/api/state') as res:return (await res.json())['csrf']
    async def test_pin_screen_and_protected_controller(self):
        async with self.c.get(self.url+'/pair') as res:
            self.assertEqual(res.status,200)
            html=await res.text()
            self.assertIn('PIN exibido na TV',html)
            self.assertNotIn('qr-mock',html)
            self.assertNotIn('panel-gamepad',html)
        async with self.c.get(self.url+'/control',allow_redirects=False) as res:
            self.assertEqual(res.status,302)
            self.assertEqual(res.headers['Location'],'/pair')
        csrf=await self.login()
        async with self.c.get(self.url+'/control') as res:
            self.assertEqual(res.status,200)
            controller=await res.text()
            self.assertIn('panel-remote',controller)
            self.assertIn('panel-gamepad',controller)
            self.assertIn('logoutBtn',controller)
            self.assertNotIn('id="pin"',controller)
        async with self.c.get(self.url+'/pair.js') as res:
            self.assertEqual(res.status,200)
        async with self.c.get(self.url+'/gamepad-editor.js') as res:
            self.assertEqual(res.status,200)
            self.assertIn('batocera-smart-remote-gamepad-v3',await res.text())
        async with self.c.get(self.url+'/control.html') as res:
            self.assertEqual(res.status,404)
        async with self.c.post(self.url+'/api/logout',json={},headers={'X-CSRF-Token':csrf}) as res:
            self.assertEqual(res.status,200)
        async with self.c.get(self.url+'/control',allow_redirects=False) as res:
            self.assertEqual(res.status,302)

    async def test_security_and_inputs(self):
        async with self.c.get(self.url+'/api/state') as res:self.assertEqual(res.status,401)
        with self.assertRaises(WSServerHandshakeError):await self.c.ws_connect(self.url+'/ws')
        async with self.c.post(self.url+'/api/pair',json={'pin':'000000'},headers={'Origin':'http://evil.test'}) as res:self.assertEqual(res.status,403)
        csrf=await self.login()
        async with self.c.post(self.url+'/api/logout',json={}) as res:self.assertEqual(res.status,403)
        ws=await self.c.ws_connect(self.url+'/ws');await ws.send_json({'type':'hello','v':1,'csrf':csrf});self.assertEqual((await ws.receive_json())['type'],'ready')
        with self.assertRaises(WSServerHandshakeError):await self.c.ws_connect(self.url+'/ws')
        await ws.send_json({'v':1,'seq':1,'type':'button','control':'UP','phase':'down'});await ws.receive_json();self.assertIn('UP',self.backend.held)
        await ws.close();await asyncio.sleep(.05);self.assertFalse(self.backend.held)
        ws=await self.c.ws_connect(self.url+'/ws');await ws.send_json({'type':'hello','v':1,'csrf':csrf});await ws.receive_json()
        await ws.send_json({'v':1,'seq':1,'type':'mode','mode':'gamepad'});await ws.receive_json()
        await ws.send_json({'v':1,'seq':1,'type':'button','control':'A','phase':'down'});self.assertEqual((await ws.receive_json())['type'],'error');await ws.close();self.assertFalse(self.backend.held)
        await self.r.revoke()
        async with self.c.get(self.url+'/api/state') as res:self.assertEqual(res.status,401)

if __name__=='__main__':unittest.main(verbosity=2)
