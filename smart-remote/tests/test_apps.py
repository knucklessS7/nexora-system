import asyncio,sys,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import apps
from aiohttp import web

class LaunchTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.active=False;self.launches=0;self.stops=0;self.delay=.1;self.fail_stop=False
  async def running(r):return web.json_response({'path':'/fake/app'} if self.active else {'msg':'NO GAME RUNNING'},status=200 if self.active else 201)
  async def idle(r):return web.json_response([not self.active])
  async def launch(r):
   self.launches+=1
   await asyncio.sleep(self.delay);self.active=True
   return web.Response()
  async def stop(r):
   self.stops+=1
   if not self.fail_stop:self.active=False
   return web.Response()
  app=web.Application();app.router.add_get('/runningGame',running);app.router.add_get('/isIdle',idle);app.router.add_post('/launch',launch);app.router.add_get('/emukill',stop);app.router.add_get('/aura/home',idle)
  self.runner=web.AppRunner(app);await self.runner.setup();site=web.TCPSite(self.runner,'127.0.0.1',0);await site.start()
  self.launcher=apps.Launcher('http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]))
  self.patch=patch.object(apps,'catalog',AsyncMock(return_value={'Disney':'/fake/disney','Netflix':'/fake/netflix'}));self.patch.start()
 async def asyncTearDown(self):self.patch.stop();await self.runner.cleanup()
 async def test_open_block_home_then_open(self):
  await self.launcher.launch('Disney')
  with self.assertRaises(apps.AppError):await self.launcher.launch('Netflix')
  self.assertEqual(self.launches,1)
  await self.launcher.home();self.assertFalse(self.active)
  await self.launcher.launch('Netflix');self.assertEqual(self.launches,2);self.assertEqual(self.stops,1)
 async def test_parallel_launches(self):
  self.delay=.3
  task=asyncio.create_task(self.launcher.launch('Disney'));await asyncio.sleep(.05)
  with self.assertRaises(apps.AppError):await self.launcher.launch('Netflix')
  await task;self.assertEqual(self.launches,1)
 async def test_ambiguous_launch_blocks(self):
  self.launcher.uncertain=True
  with self.assertRaises(apps.AppError):await self.launcher.launch('Netflix')
  self.assertEqual(self.launches,0)
  await self.launcher.home();self.assertFalse(self.launcher.uncertain)
 async def test_existing_app_not_from_remote(self):
  self.active=True
  with self.assertRaises(apps.AppError):await self.launcher.launch('Netflix')
  self.assertEqual(self.launches,0)
if __name__=='__main__':unittest.main(verbosity=2)
