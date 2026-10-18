"""Isolated browser games and explicit laptop pairing for the hosted build."""
import asyncio
import contextlib
import json
import os
import secrets
import time
from fastapi import WebSocketDisconnect

sessions={}

def enabled():return os.getenv('SPACE_ODYSSEY_HOSTED','false').lower()=='true'

def allowed_origin(origin):
    from urllib.parse import urlparse
    host=urlparse(origin).hostname
    allowed={'localhost','127.0.0.1','::1','spaceodyssey.work','www.spaceodyssey.work'}
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):allowed.add(os.environ['RENDER_EXTERNAL_HOSTNAME'])
    return not origin or host in allowed

async def browser_game(ws, engine_factory):
    if not allowed_origin(ws.headers.get('origin','')):
        await ws.close(code=1008);return
    if len(sessions)>=32:
        await ws.close(code=1013);return
    await ws.accept()
    e=engine_factory();e.simulated=True;e.sim=None;e.flight.simulated=True
    token=secrets.token_urlsafe(24)
    e.status.update(mode='HOSTED',usb=False,pairing_code=token,vision='Pair your laptop to use camera and remotes')
    sessions[token]=e;e.clients.add(ws)
    e.tasks=[asyncio.create_task(e.consume()),asyncio.create_task(e.clock())]
    try:
        while True:
            data=await ws.receive_json();command=data.get('command','')
            if not isinstance(command,str) or len(command)>120:continue
            if not command.startswith('FLIGHT,'):continue
            if command in ('FLIGHT,REGENERATE','FLIGHT,SURFACE_GAME'):
                now=time.monotonic()
                if now-getattr(e,'last_generation_request',-100)<8:continue
                e.last_generation_request=now
            with contextlib.suppress(ValueError,TypeError):e.control(command)
    except (WebSocketDisconnect,RuntimeError,json.JSONDecodeError):pass
    finally:
        sessions.pop(token,None)
        bridge=getattr(e,'paired_socket',None)
        if bridge:
            with contextlib.suppress(Exception):await bridge.close(code=1001)
        await e.close()

async def laptop_bridge(ws):
    # The high-entropy, short-lived code is displayed only to the owning game.
    await ws.accept();e=None
    try:
        hello=await asyncio.wait_for(ws.receive_json(),5)
        token=hello.get('pairing_code')
        e=sessions.get(token) if isinstance(token,str) else None
        if e is None or getattr(e,'paired_socket',None):
            await ws.close(code=1008);return
        e.paired_socket=ws
        await ws.send_json({'paired':True})
        while True:
            data=await ws.receive_json()
            kind=data.get('kind');value=data.get('data')
            if kind=='line' and isinstance(value,str) and len(value)<100 and value.startswith('REMOTE,'):
                e.submit('line',value)
            elif kind=='input' and isinstance(value,str) and value in {f'INPUT,P{i},{a}' for i in (1,2) for a in ('JUMP','DUCK_ON','DUCK_OFF')}:
                e.submit('input',value)
            elif kind=='status' and isinstance(value,dict):
                e.status['usb']=value.get('usb') is True
                e.status['vision']=str(value.get('vision','Camera not connected'))[:160]
                e.external_camera_last=time.monotonic();e.external_camera_expired=False
            else:continue
    except (WebSocketDisconnect,RuntimeError,asyncio.TimeoutError,json.JSONDecodeError):pass
    finally:
        if e and getattr(e,'paired_socket',None) is ws:
            e.paired_socket=None;e.status.update(usb=False,vision='Laptop disconnected — pair again')
            for p in ('P1','P2'):
                e.flight.command(f'FLIGHT,{p},DISCONNECTED',source='remote')
                e.flight.command(f'FLIGHT,{p},DUCK_OFF',source='vision')

async def forward_to_host(engine):
    """Outbound TLS only; never opens laptop ports to the public internet."""
    import websockets
    from urllib.parse import urlparse
    url=os.getenv('SPACE_ODYSSEY_HOST_URL','').rstrip('/')
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in {'spaceodyssey.work','www.spaceodyssey.work'} and not (parsed.hostname or '').endswith('.onrender.com'):
        engine.status['cloud']='Invalid host URL';return
    endpoint='wss://'+parsed.netloc+'/ws/bridge'
    queue=engine.cloud_queue
    while True:
        try:
            async with websockets.connect(endpoint,max_size=8192) as ws:
                await ws.send(json.dumps({'pairing_code':os.environ['SPACE_ODYSSEY_PAIRING_CODE']}))
                response=json.loads(await asyncio.wait_for(ws.recv(),5))
                if not response.get('paired'):raise ValueError('Pair rejected')
                engine.status['cloud']='Paired'
                while True:
                    try:
                        at,kind,data=await asyncio.wait_for(queue.get(),timeout=.5)
                        if time.monotonic()-at<.25:await ws.send(json.dumps({'kind':kind,'data':data}))
                    except asyncio.TimeoutError:pass
                    now=time.monotonic()
                    if now-getattr(engine,'cloud_status_at',0)>.5:
                        engine.cloud_status_at=now
                        await ws.send(json.dumps({'kind':'status','data':{'usb':engine.status['usb'],'vision':engine.status['vision']}}))
        except asyncio.CancelledError:raise
        except Exception:
            engine.status['cloud']='Not paired — check code and connection'
            await asyncio.sleep(2)
