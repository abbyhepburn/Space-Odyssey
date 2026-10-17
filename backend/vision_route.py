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


def require_local(request: Request):
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
    return {'ok': True, 'ready': payload.ready}


@router.post('/api/vision/event')
async def camera_event(payload: CameraEvent, request: Request):
    require_local(request)
    engine = request.app.state.engine
    # Do not fake a game state here; route through the *existing* authority.
    engine.submit('input', f'INPUT,{payload.player},{payload.action}')
    return {'ok': True}


def expire_camera(engine, now):
    """Fail closed on unplugged iPhone/camera when physical Pico is enabled."""
    last = getattr(engine, 'external_camera_last', None)
    if last is None or now - last <= 3.5 or getattr(engine, 'external_camera_expired', False):
        return
    engine.external_camera_expired = True
    engine.status['vision'] = 'Camera disconnected — keyboard controls still available'
    update_capabilities(engine, False)
    # Release duck state so a disconnected camera doesn't leave a player crouched.
    engine.submit('input', 'INPUT,P1,DUCK_OFF')
    engine.submit('input', 'INPUT,P2,DUCK_OFF')
