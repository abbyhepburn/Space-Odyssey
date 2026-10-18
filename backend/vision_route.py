"""Local-only camera process -> existing Space Odyssey input queue.

Works with the *existing* Engine.consume() handler in backend/main.py.
No React changes, image streaming, or Gemini calls are required.
"""
import contextlib
import time
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()
LOOPBACK = {'127.0.0.1', '::1'}


class CameraEvent(BaseModel):
    player: Literal['P1', 'P2']
    action: Literal['JUMP', 'DUCK_ON', 'DUCK_OFF']


class CameraHeartbeat(BaseModel):
    ready: bool
    detail: str = Field(default='', max_length=120)
    ducks: list[bool] | None = Field(default=None, min_length=2, max_length=2)


def require_local(request: Request):
    import hosted
    if hosted.enabled():raise HTTPException(403,'Camera runs on your paired laptop, not the hosting server')
    if request.client is None or request.client.host not in LOOPBACK:
        raise HTTPException(403, 'Camera events only accepted from this computer')


def update_capabilities(engine, ready):
    if engine.vision is not None:
        # Don't run two camera workers simultaneously.
        return
    caps = {'jump': bool(ready or engine.simulated),
            'duck': bool(ready or engine.simulated)}
    if engine.capabilities != caps:
        engine.capabilities = caps
        with contextlib.suppress(ValueError):
            engine.send(f'CAPABILITIES,{int(caps["jump"])},{int(caps["duck"])}')


@router.post('/api/vision/heartbeat')
async def camera_heartbeat(payload: CameraHeartbeat, request: Request):
    require_local(request)
    engine = request.app.state.engine
    engine.external_camera_last = time.monotonic()
    engine.external_camera_expired = False
    engine.status['vision'] = ('Camera ready' if payload.ready else 'Camera calibrating') + (
        f' — {payload.detail}' if payload.detail else '')
    update_capabilities(engine, payload.ready)
    if payload.ducks is not None:
        for i,duck in enumerate(payload.ducks):
            engine.submit('input', f'INPUT,P{i+1},'+('DUCK_ON' if duck else 'DUCK_OFF'))
    elif not payload.ready:
        for player in ('P1','P2'):engine.submit('input', f'INPUT,{player},DUCK_OFF')
    return {'ok': True, 'ready': payload.ready}


@router.post('/api/vision/event')
async def camera_event(payload: CameraEvent, request: Request):
    require_local(request)
    engine = request.app.state.engine
    if engine.vision is not None:
        raise HTTPException(409, 'Disable VISION_ENABLED before using the standalone camera')
    engine.external_camera_last = time.monotonic()
    engine.external_camera_expired = False
    # Do not fake a game state here; route through the *existing* authority.
    engine.submit('input', f'INPUT,{payload.player},{payload.action}')
    return {'ok': True}


def expire_camera(engine, now):
    """Fail closed on unplugged iPhone/camera when physical Pico is enabled."""
    process=getattr(engine,'camera_process',None)
    if process is not None and process.returncode is not None and not getattr(engine,'camera_exit_reported',False):
        engine.camera_exit_reported=True
        engine.status['vision']='Camera preview closed or failed — reopen camera; check backend/camera-preview.log and camera permission'
    last = getattr(engine, 'external_camera_last', None)
    if last is None or now - last <= 3.5 or getattr(engine, 'external_camera_expired', False):
        return
    engine.external_camera_expired = True
    engine.status['vision'] = 'Camera disconnected — keyboard controls still available'
    update_capabilities(engine, False)
    # Release duck state so a disconnected camera doesn't leave a player crouched.
    engine.submit('input', 'INPUT,P1,DUCK_OFF')
    engine.submit('input', 'INPUT,P2,DUCK_OFF')

@router.post('/api/vision/start')
async def start_camera(request: Request):
    """User-triggered local camera process; preview never enters the game canvas."""
    import asyncio
    import os
    import sys
    from pathlib import Path
    from urllib.parse import urlparse
    require_local(request)
    origin=request.headers.get('origin')
    if origin and urlparse(origin).hostname not in LOOPBACK|{'localhost'}:
        raise HTTPException(403,'Start the camera from the local game')
    engine=request.app.state.engine
    if engine.vision is not None:
        raise HTTPException(409,'Disable VISION_ENABLED to use the separate laptop preview')
    process=getattr(engine,'camera_process',None)
    if process is not None and process.returncode is None:
        return {'ok':True,'detail':'Camera window is already running on your laptop'}
    if time.monotonic()-getattr(engine,'external_camera_last',-100)<3.5:
        return {'ok':True,'detail':'Camera is already connected'}
    root=Path(__file__).parent
    from download_pose_model import MODEL_PATH
    if not MODEL_PATH.exists():
        raise HTTPException(409,'Pose model missing. Run backend/download_pose_model.py once, then retry.')
    import importlib.util
    if any(importlib.util.find_spec(name) is None for name in ('cv2','mediapipe')):
        raise HTTPException(409,'Install backend/requirements-vision.txt in the backend environment, then retry.')
    # Use the actual backend listener, not untrusted browser-supplied arguments.
    port=request.scope.get('server',('127.0.0.1',8000))[1]
    log=root/'camera-preview.log'
    with log.open('ab') as output:
        engine.camera_process=await asyncio.create_subprocess_exec(sys.executable,str(root/'camera_vision.py'),'--camera',os.getenv('CAMERA_INDEX','0'),'--backend',f'http://127.0.0.1:{port}',stdout=output,stderr=output,cwd=str(root))
    engine.camera_exit_reported=False
    engine.status['vision']='Starting camera — check laptop preview and camera permission'
    return {'ok':True,'detail':engine.status['vision']}

async def stop_camera_process(engine):
    import asyncio
    process=getattr(engine,'camera_process',None)
    if process is not None and process.returncode is None:
        process.terminate()
        try:await asyncio.wait_for(process.wait(),3)
        except asyncio.TimeoutError:
            process.kill();await process.wait()
