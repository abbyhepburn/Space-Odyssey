from vision_route import router as vision_router, expire_camera
"""Thread callbacks -> asyncio queue -> authority -> parsed snapshots -> WebSockets."""
import asyncio
import contextlib
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Literal
from protocol import State, parse_line, command_line
from simulator import Simulator
from serial_bridge import SerialBridge
from gemini_missions import generate
from vision import VisionWorker
from exploration import Exploration
from flight_game import FlightGame
from control_inputs import remote_to_flight
import hosted

load_dotenv(os.getenv('SPACE_ODYSSEY_ENV', str(Path(__file__).with_name('.env'))))

class Control(BaseModel):
    command: str

class Engine:
    def __init__(self):
        self.simulated=os.getenv('SIMULATE_PICO','true').lower()=='true'
        self.sim=Simulator() if self.simulated else None
        self.exploration=Exploration(self.simulated)
        self.flight=FlightGame(self.simulated)
        self.state=vars(State()).copy(); self.queue=asyncio.Queue(maxsize=2048)
        self.cloud_queue=asyncio.Queue(maxsize=128)
        self.clients=set(); self.bridge=None; self.vision=None; self.tasks=[]
        self.capabilities={'jump':True,'duck':True}
        self.status={'usb':self.simulated,'mode':'SIMULATOR' if self.simulated else 'PICO USB','vision':'Remote controls ready','gemini':'Local mission catalog','message':''}
        self.active=None; self.pending=None; self.mission_index=0; self.generating=False; self.epoch=0; self.last_state=0
        self.retry_at=0; self.mission_task=None

    def snapshot(self):
        return {'type':'snapshot','state':self.state,'mission':self.active,'pending':bool(self.pending) or self.generating,'status':self.status,'capabilities':self.capabilities,'exploration':self.exploration.snapshot(),'flight':self.flight.snapshot()}

    def submit(self, kind, data):
        if os.getenv('SPACE_ODYSSEY_HOST_URL') and kind in ('line','input'):
            with contextlib.suppress(asyncio.QueueFull):self.cloud_queue.put_nowait((time.monotonic(),kind,data))
        # Scheduled on event loop by thread-safe callbacks; bounded queue drops overload.
        with contextlib.suppress(asyncio.QueueFull): self.queue.put_nowait((kind,data))

    def send(self, command):
        command_line(command)
        if self.sim:
            for line in self.sim.command(command): self.submit('line',line)
        elif self.bridge and self.status['usb']: self.bridge.send(command)
        else: raise ValueError('Pico is disconnected')

    def control(self, command):
        if command.startswith('VISION,'):
            parts=command.split(',')
            if len(parts)!=3 or parts[1] not in ('P1','P2') or parts[2] not in ('JUMP','DUCK_ON','DUCK_OFF'):
                raise ValueError('Invalid remote action event')
            self.external_camera_last=time.monotonic();self.external_camera_expired=False
            self.status['vision']='Remote controls active'
            self.flight.command(f'FLIGHT,{parts[1]},{parts[2]}',source='vision')
            return

        # Developer can emulate a remote over local WebSocket/API for tests.
        # The same REMOTE message format is accepted from the Pico USB reader.
        if command.startswith('REMOTE,'):
            self.flight.command(remote_to_flight(command),source='remote');return
        if command.startswith("FLIGHT,"):
            self.flight.command(command); return
        if command.startswith(('PLANET,','MISSION_','ACTION,')):
            self.exploration.command(command); return
        command_line(command)
        if command.startswith(('SET_MISSION','CAPABILITIES')): raise ValueError('Reserved backend command')
        if command.startswith('INPUT') and not self.simulated:
            raise ValueError('Simulator inputs require simulator mode; prevents duplicate BLE run events')
        if command=='RESET':
            self.epoch+=1; self.active=None; self.pending=None
        self.send(command)

    async def request_mission(self):
        if self.state['phase']!='RACE' or self.active or self.pending or self.generating: return False
        self.generating=True; epoch=self.epoch
        try:
            mission,status=await generate(dict(self.capabilities),self.mission_index)
            if epoch!=self.epoch or self.state['phase']!='RACE': return False
            mission.compatible(self.state['phase'],self.capabilities)
            self.status['gemini']=status
            self.pending={'data':mission.model_dump(),'deadline':time.monotonic()+3}
            self.send(f'SET_MISSION,{mission.mission_id},{mission.target},{mission.time_limit_s}')
            self.mission_index+=1
            return True
        except Exception as exc:
            self.pending=None; self.status['message']=str(exc); self.retry_at=time.monotonic()+3
            return False
        finally: self.generating=False

    def launch_mission(self):
        if self.mission_task is None or self.mission_task.done(): self.mission_task=asyncio.create_task(self.request_mission())

    async def consume(self):
        while True:
            kind,data=await self.queue.get()
            if kind=='input':
                with contextlib.suppress(ValueError):
                    parts=data.split(',')
                    if len(parts)==3 and parts[0]=='INPUT' and parts[1] in ('P1','P2'):
                        # Camera and keyboard feed the same authority in all phases.
                        # Held duck may begin during the preparation countdown.
                        self.flight.command(f'FLIGHT,{parts[1]},{parts[2]}',source='vision')
            elif kind=='usb':
                connected,message=data; self.status.update(usb=connected,message=message)
                if connected:
                    self.last_state=time.monotonic()
                    self.send(f"CAPABILITIES,{int(self.capabilities['jump'])},{int(self.capabilities['duck'])}")
                else:
                    for player in ('P1','P2'):self.flight.command(f'FLIGHT,{player},DISCONNECTED',source='remote')
                    self.epoch+=1; self.active=None; self.pending=None
            elif kind=='vision':
                ready,message=data; self.status['vision']=message
                caps={'jump':ready or self.simulated,'duck':ready or self.simulated}
                if caps!=self.capabilities:
                    self.capabilities=caps
                    with contextlib.suppress(ValueError): self.send(f'CAPABILITIES,{int(caps["jump"])},{int(caps["duck"])}')
            elif kind=='line':
                if data.startswith('REMOTE,'):
                    # Firmware motion signals and keyboard test controls converge
                    # on the same authoritative gameplay without separate rules.
                    try:
                        self.flight.command(remote_to_flight(data),source='remote')
                    except ValueError:
                        self.status['message']='Ignored invalid remote event'
                    continue
                event=parse_line(data)
                if event is None: continue
                et=event['type']
                if et=='hello':
                    self.epoch+=1; self.active=None; self.pending=None
                    self.send(f"CAPABILITIES,{int(self.capabilities['jump'])},{int(self.capabilities['duck'])}")
                elif et=='state':
                    old=self.state; self.state=event['state']; self.last_state=time.monotonic()
                    if self.state['phase']!='RACE':
                        self.active=None; self.pending=None
                        if old['phase']=='RACE': self.epoch+=1
                    if self.active and self.state['mission_id']!=self.active['mission_id']: self.active=None
                elif et=='mission_accepted' and self.pending and event['mission_id']==self.pending['data']['mission_id']:
                    self.active={**self.pending['data'],'started_ms':self.state['elapsed_ms'],'origin1':self.state['p1_distance'],'origin2':self.state['p2_distance']}
                    self.pending=None; self.status['message']='Challenge accepted by game authority'
                elif et=='mission_rejected':
                    self.pending=None; self.status['message']='Mission rejected: '+event['reason']; self.retry_at=time.monotonic()+3
                elif et=='event' and event['kind']=='MISSION_ENDED': self.active=None
                if et!='state': self.status['last_event']=event

    async def clock(self):
        last=time.monotonic()
        while True:
            await asyncio.sleep(.05); now=time.monotonic()
            self.flight.tick(now-last)
            expire_camera(self,now)
            if self.sim:
                for line in self.sim.tick(max(1,round((now-last)*1000))): self.submit('line',line)
            last=now
            self.status['state_fresh']=now-self.last_state<2
            if self.pending and now>self.pending['deadline']:
                self.pending=None; self.status['message']='Mission acknowledgement timed out'; self.retry_at=now+5
            # The authority must clear mission_id before another mission can be requested.
            payload=self.snapshot()
            async def deliver(ws):
                try: await asyncio.wait_for(ws.send_json(payload),timeout=.2)
                except Exception: self.clients.discard(ws)
            await asyncio.gather(*(deliver(ws) for ws in tuple(self.clients)))

    async def start(self):
        loop=asyncio.get_running_loop()
        def callback(kind): return lambda *data: loop.call_soon_threadsafe(self.submit,kind,data[0] if len(data)==1 else data)
        if not self.simulated:
            self.bridge=SerialBridge(os.getenv('SERIAL_PORT',''),callback('line'),callback('usb')); self.bridge.start()
        # Jump and duck come from the remotes; do not start an OpenCV worker.
        self.tasks=[asyncio.create_task(self.consume()),asyncio.create_task(self.clock())]
        if os.getenv('SPACE_ODYSSEY_HOST_URL'):self.tasks.append(asyncio.create_task(hosted.forward_to_host(self)))
    async def close(self):
        from vision_route import stop_camera_process
        await stop_camera_process(self)
        if self.flight.task:
            self.flight.task.cancel()
            await asyncio.gather(self.flight.task,return_exceptions=True)
        if self.exploration.task:
            self.exploration.task.cancel()
            await asyncio.gather(self.exploration.task,return_exceptions=True)
        for worker in (self.vision,self.bridge):
            if worker: await asyncio.to_thread(worker.close)
        for task in self.tasks+([self.mission_task] if self.mission_task else []): task.cancel()
        await asyncio.gather(*self.tasks,*([self.mission_task] if self.mission_task else []),return_exceptions=True)

@asynccontextmanager
async def lifespan(app):
    app.state.engine=Engine(); await app.state.engine.start()
    yield
    await app.state.engine.close()

app=FastAPI(title='Space Odyssey',lifespan=lifespan)
app.include_router(vision_router)
@app.get('/health')
async def health():
    e=app.state.engine
    return {'ok':True,**e.status,'flight_gemini':e.flight.source or 'NOT GENERATED YET'}
@app.get('/state')
async def state(): return app.state.engine.snapshot()
@app.get('/api/flight/gemini-status')
async def flight_gemini_status():
    """Local debugging without exposing the user's key or raw API responses."""
    import importlib.util
    try:
        sdk_available = importlib.util.find_spec('google.genai') is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        sdk_available = False
    game = app.state.engine.flight
    source = game.source or 'NOT GENERATED YET'
    return {
        'api_key_configured': bool(os.getenv('GEMINI_API_KEY', '').strip()),
        'sdk_installed': sdk_available,
        'configured_model': os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'),
        'last_flight_mission_source': source,
        'generating_now': game.phase == 'GENERATING',
        'hint': (
            'No key found in backend/.env; only local games can be generated.'
            if not os.getenv('GEMINI_API_KEY', '').strip()
            else 'The API key is configured; generate a planet challenge to check whether it is used.'
        ),
    }

@app.post('/api/missions/generate')
async def missions():
    if hosted.enabled():raise HTTPException(403,'Use your private game connection')
    e=app.state.engine
    if e.state['phase']!='RACE' or e.active or e.pending or e.generating: raise HTTPException(409,'Wait for the next mission boundary')
    e.launch_mission(); return {'queued':True}
@app.post('/api/control')
async def control(body:Control):
    if hosted.enabled():raise HTTPException(403,'Use your private game connection')
    try: app.state.engine.control(body.command)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {'ok':True}
@app.websocket('/ws/game')
async def game(ws:WebSocket):
    if hosted.enabled():
        await hosted.browser_game(ws,Engine);return
    # Local-only server; prevent unrelated browser sites driving attached hardware.
    origin=ws.headers.get('origin','')
    from urllib.parse import urlparse
    if origin and urlparse(origin).hostname not in {'localhost','127.0.0.1','::1'}:
        await ws.close(code=1008); return
    await ws.accept(); e=app.state.engine; e.clients.add(ws)
    try:
        while True:
            data=await ws.receive_json()
            try:
                if data.get('command')=='GENERATE':
                    if e.active or e.pending or e.state['phase']!='RACE': raise ValueError('Wait for a mission boundary')
                    e.launch_mission()
                elif data.get('command')=='VISION_DEBUG':
                    if not e.vision: raise ValueError('Enable VISION_ENABLED in backend/.env first')
                    e.vision.debug=not e.vision.debug
                elif data.get('command')=='CALIBRATE':
                    if not e.vision: raise ValueError('Vision is disabled')
                    e.vision.recalibrate.set()
                else: e.control(Control.model_validate(data).command)
            except (ValueError,TypeError) as exc: e.status['message']=str(exc)
    except (WebSocketDisconnect,RuntimeError): pass
    finally: e.clients.discard(ws)

@app.websocket('/ws/bridge')
async def bridge_socket(ws:WebSocket):
    if not hosted.enabled():
        await ws.close(code=1008);return
    await hosted.laptop_bridge(ws)

# Serve the exact production build beside its API and WebSocket endpoint.
from fastapi.staticfiles import StaticFiles
static_dir=Path(__file__).resolve().parent.parent/'frontend'/'dist'
if static_dir.exists():app.mount('/',StaticFiles(directory=static_dir,html=True),name='game')
