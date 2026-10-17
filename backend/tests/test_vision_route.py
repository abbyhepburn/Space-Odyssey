"""Lightweight local-route checks, no webcam, model, or real server needed."""
import asyncio
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from vision_route import (CameraEvent, CameraHeartbeat, camera_event,
                          camera_heartbeat, expire_camera)


class Engine:
    def __init__(self):
        self.received=[]
        self.status={'vision':'Disabled'}
        self.capabilities={'jump':True,'duck':True}
        self.simulated=True
        self.vision=None

    def submit(self, kind, data):
        self.received.append((kind,data))


def request(engine, host='127.0.0.1'):
    return SimpleNamespace(client=SimpleNamespace(host=host),
                           app=SimpleNamespace(state=SimpleNamespace(engine=engine)))


def test_camera_event_uses_existing_input_queue():
    engine=Engine()
    result=asyncio.run(camera_event(CameraEvent(player='P2',action='DUCK_ON'),request(engine)))
    assert result == {'ok': True}
    assert engine.received == [('input','INPUT,P2,DUCK_ON')]


def test_network_access_must_be_local():
    with pytest.raises(HTTPException) as err:
        asyncio.run(camera_event(CameraEvent(player='P1',action='JUMP'),request(Engine(),'192.168.1.5')))
    assert err.value.status_code == 403


def test_heartbeat_then_camera_dropout_releases_duck():
    e=Engine()
    asyncio.run(camera_heartbeat(CameraHeartbeat(ready=True,detail='players visible'),request(e)))
    assert 'Camera ready' in e.status['vision']
    expire_camera(e,e.external_camera_last+4.0)
    assert ('input','INPUT,P1,DUCK_OFF') in e.received
    assert ('input','INPUT,P2,DUCK_OFF') in e.received
    assert 'disconnected' in e.status['vision']
