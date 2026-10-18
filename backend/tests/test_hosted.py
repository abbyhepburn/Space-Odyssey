import time
import pytest
from fastapi.testclient import TestClient
from main import app
import hosted

def until(ws, predicate):
    for _ in range(80):
        snapshot=ws.receive_json()
        if predicate(snapshot):return snapshot
    raise AssertionError('Expected snapshot not received')

def test_hosted_sessions_are_isolated_and_bridge_is_authenticated(monkeypatch):
    monkeypatch.setenv('SPACE_ODYSSEY_HOSTED','true')
    monkeypatch.setenv('SIMULATE_PICO','true')
    monkeypatch.setenv('VISION_ENABLED','false')
    with TestClient(app) as client:
        assert client.post('/api/control',json={'command':'FLIGHT,LAUNCH'}).status_code==403
        with client.websocket_connect('/ws/game') as one, client.websocket_connect('/ws/game') as two:
            first=one.receive_json();second=two.receive_json()
            code=first['status']['pairing_code']
            assert code!=second['status']['pairing_code']
            one.send_json({'command':'FLIGHT,LAUNCH'})
            until(one,lambda s:s['flight']['phase']=='LAUNCH')
            assert two.receive_json()['flight']['phase']=='READY'
            with client.websocket_connect('/ws/bridge') as bridge:
                bridge.send_json({'pairing_code':code})
                assert bridge.receive_json()['paired']
                bridge.send_json({'kind':'line','data':'REMOTE,P2,STATE,0.2,-0.4,0.8'})
                snapshot=until(one,lambda s:s['flight']['controllers'][1]['fresh'])
                assert snapshot['flight']['controllers'][1]['raw']==[.2,-.4,.8]
                bridge.send_json({'kind':'input','data':'INPUT,P1,DUCK_ON'})
                until(one,lambda s:s['flight']['players'][0]['duck'])
            until(one,lambda s:not s['flight']['players'][0]['duck'])
            assert not two.receive_json()['flight']['controllers'][1]['fresh']
    assert not hosted.sessions

def test_hosted_rejects_other_websites(monkeypatch):
    monkeypatch.setenv('SPACE_ODYSSEY_HOSTED','true')
    with TestClient(app) as client:
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws/game',headers={'origin':'https://unrelated.example'}):pass
