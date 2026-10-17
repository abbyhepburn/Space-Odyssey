import asyncio
from fastapi.testclient import TestClient
from main import app,Engine

def test_endpoints_and_websocket():
    with TestClient(app) as client:
        assert client.get('/health').status_code==200
        assert client.post('/api/missions/generate').status_code==409
        assert client.post('/api/control',json={'command':'INPUT,P3,RUN'}).status_code==400
        with client.websocket_connect('/ws/game') as ws:
            assert ws.receive_json()['type']=='snapshot'
            ws.send_json({'command':'SKIP_CUTSCENE'})
            for _ in range(10):
                frame=ws.receive_json()
                if frame['state']['phase']=='COUNTDOWN':break
            assert frame['state']['phase']=='COUNTDOWN'


def test_pending_mission_not_active_until_ack():
    async def scenario():
        e=Engine();e.state['phase']='RACE';e.sim.tick(9000);e.sim.tick(3000)
        await e.request_mission()
        assert e.pending and e.active is None
        task=asyncio.create_task(e.consume());await asyncio.sleep(.01)
        assert e.active and e.pending is None
        task.cancel();await asyncio.gather(task,return_exceptions=True)
    asyncio.run(scenario())
