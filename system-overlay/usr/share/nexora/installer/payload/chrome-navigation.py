#!/usr/bin/env python3
"""AURA V6: CDP navigation with reusable per-document JS context.

Preserves the existing navigation JS and Xbox mapping. Recreates its isolated
world only after a real document change, rather than every two seconds.
No Chrome, DRM, profile, account, shortcut or theme modifications.
"""
import asyncio
import json
import sys
from pathlib import Path

import aiohttp

CALIBRATION = Path('/tmp/aura-controller-calibration.json')


def calibration_message(path=CALIBRATION):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        value = data.get('message') if isinstance(data, dict) else None
        return value[:300] if isinstance(value, str) else None
    except (OSError, ValueError, UnicodeError):
        return None


class DocumentState:
    def __init__(self):
        self.frame_id = None
        self.loader_id = None
        self.context_id = None
        self.last_calibration = None

    def reset(self):
        self.frame_id = self.loader_id = self.context_id = None


async def update_document(call, script, state, message=None):
    """Refresh an existing context; inject only after initial attach/reload.

    Page.addScriptToEvaluateOnNewDocument handles the actual document events.
    Page.getFrameTree loaderId catches reloads missed between polls.
    """
    tree = (await call('Page.getFrameTree')).get('frameTree', {}).get('frame', {})
    frame_id = tree.get('id')
    loader_id = tree.get('loaderId')
    if not frame_id:
        raise RuntimeError('CDP main frame not ready')
    if state.context_id is None or state.frame_id != frame_id or state.loader_id != loader_id:
        result = await call('Page.createIsolatedWorld', {
            'frameId': frame_id, 'worldName': 'AuraNavigation'})
        context_id = result.get('executionContextId')
        if not isinstance(context_id, int) or context_id <= 0:
            raise RuntimeError('CDP context not ready')
        state.frame_id, state.loader_id, state.context_id = frame_id, loader_id, context_id
        state.last_calibration = None
        await call('Runtime.evaluate', {'expression': script, 'contextId': context_id})
    else:
        # Keeps the original 2s SPA/Netflix focus refresh without recreating worlds.
        await call('Runtime.evaluate', {
            'expression': 'window.__auraChromeNavRefresh?.()', 'contextId': state.context_id})
    if message is not None and message != state.last_calibration:
        await call('Runtime.evaluate', {
            'expression': 'window.__auraCalibrationStatus?.(' + json.dumps(message) + ')',
            'contextId': state.context_id})
        state.last_calibration = message


async def attach(session, target, script):
    async with session.ws_connect(target['webSocketDebuggerUrl'], max_msg_size=4 * 1024 * 1024) as ws:
        seq = 0

        async def call(method, params=None):
            nonlocal seq
            seq += 1
            request_id = seq
            await ws.send_json({'id': request_id, 'method': method, 'params': params or {}})
            while True:
                reply = await asyncio.wait_for(ws.receive_json(), timeout=5)
                if reply.get('id') != request_id:
                    continue  # Chrome asynchronously sends event messages too.
                if 'error' in reply:
                    raise RuntimeError(reply['error'].get('message', 'CDP error'))
                return reply.get('result', {})

        await call('Page.enable')
        await call('Page.addScriptToEvaluateOnNewDocument', {
            'source': script, 'worldName': 'AuraNavigation'})
        state = DocumentState()
        while True:
            try:
                await update_document(call, script, state, calibration_message())
            except RuntimeError:
                # Navigation/context transition. Retry next tick; don't stop Chrome.
                state.reset()
            await asyncio.sleep(2)


async def main(profile):
    script = Path(__file__).with_name('chrome-navigation.js').read_text(encoding='utf-8')
    endpoint = Path(profile) / 'DevToolsActivePort'
    tasks = {}
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
        try:
            while True:
                valid_targets = {}
                try:
                    port = int(endpoint.read_text(encoding='utf-8').splitlines()[0])
                    if not 0 < port < 65536:
                        raise ValueError('Invalid CDP port')
                    async with session.get('http://127.0.0.1:%d/json/list' % port) as response:
                        data = await response.json()
                    if not isinstance(data, list):
                        raise ValueError('Invalid CDP target list')
                    for target in data:
                        if not isinstance(target, dict) or target.get('type') != 'page':
                            continue
                        wsurl = target.get('webSocketDebuggerUrl', '')
                        key = target.get('id')
                        if isinstance(key, str) and key and isinstance(wsurl, str) and wsurl.startswith('ws://127.0.0.1:%d/' % port):
                            valid_targets[key] = target
                except (OSError, ValueError, IndexError, TypeError, aiohttp.ClientError, asyncio.TimeoutError):
                    # Do not drop an active page just because one local poll failed.
                    valid_targets = None

                if valid_targets is not None:
                    for key in list(tasks):
                        task = tasks[key]
                        if task.done():
                            try:
                                task.result()
                            except (Exception, asyncio.CancelledError) as error:
                                if not isinstance(error, asyncio.CancelledError):
                                    print('[AURA V6 NAV]', type(error).__name__, flush=True)
                            tasks.pop(key, None)
                        elif key not in valid_targets:
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
                            tasks.pop(key, None)
                    for key, target in valid_targets.items():
                        if key not in tasks:
                            tasks[key] = asyncio.create_task(attach(session, target, script))
                await asyncio.sleep(1)
        finally:
            for task in tasks.values():
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks.values(), return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
