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
            until(one,lambda s:s['flight']['phase']=='BOOT')
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


def test_hosted_controller_button_routes_to_only_its_browser_menu(monkeypatch):
    monkeypatch.setenv('SPACE_ODYSSEY_HOSTED','true')
    monkeypatch.setenv('SIMULATE_PICO','true')
    with TestClient(app) as client:
        with client.websocket_connect('/ws/game') as browser:
            code=browser.receive_json()['status']['pairing_code']
            browser.send_json({'command':'UI,CONTEXT,MODAL'})
            with client.websocket_connect('/ws/bridge') as bridge:
                bridge.send_json({'pairing_code':code})
                assert bridge.receive_json()['paired']
                bridge.send_json({'kind':'line','data':'REMOTE,P2,SELECT'})
                snapshot=until(browser,lambda s:s['flight']['ui_presses']==[0,1])
                assert snapshot['flight']['phase']=='READY'

def test_browser_camera_is_scoped_to_own_game_and_keyboard_does_not_release_it(monkeypatch):
    monkeypatch.setenv('SPACE_ODYSSEY_HOSTED','true')
    monkeypatch.setenv('SIMULATE_PICO','true')
    monkeypatch.setenv('VISION_ENABLED','false')
    with TestClient(app) as client:
        with client.websocket_connect('/ws/game') as one, client.websocket_connect('/ws/game') as two:
            one.receive_json();two.receive_json()
            one.send_json({'command':'VISION,P1,DUCK_ON'})
            until(one,lambda s:s['flight']['players'][0]['duck'])
            one.send_json({'command':'FLIGHT,P1,DUCK_OFF'})
            assert one.receive_json()['flight']['players'][0]['duck']
            assert not two.receive_json()['flight']['players'][0]['duck']
            one.send_json({'command':'VISION,P1,DUCK_OFF'})
            until(one,lambda s:not s['flight']['players'][0]['duck'])


def test_pairing_applies_laptop_axis_signs_to_only_its_game(monkeypatch):
    monkeypatch.setenv('SPACE_ODYSSEY_HOSTED','true')
    monkeypatch.setenv('SIMULATE_PICO','true')
    with TestClient(app) as client:
        with client.websocket_connect('/ws/game') as one, client.websocket_connect('/ws/game') as two:
            code=one.receive_json()['status']['pairing_code'];other=two.receive_json()['status']['pairing_code']
            with client.websocket_connect('/ws/bridge') as bridge:
                bridge.send_json({'pairing_code':code});assert bridge.receive_json()['paired']
                bridge.send_json({'kind':'status','data':{'usb':True,'controller_signs':[[-1,1,1],[1,1,1]]}})
                bridge.send_json({'kind':'line','data':'REMOTE,P1,STATE,0.75,0.2,0'})
                s=until(one,lambda s:s['flight']['controllers'][0]['fresh'])
                assert s['flight']['controllers'][0]['raw']==[.75,.2,0.]
                assert s['flight']['controllers'][0]['effective']==[-.75,.2]
                assert hosted.sessions[other].flight.controller_signs[0][0]==1
