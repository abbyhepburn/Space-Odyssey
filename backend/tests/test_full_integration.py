import asyncio
import math
from types import SimpleNamespace
import pytest
from flight_game import FlightGame,local_mission,ROCKY_PLANETS
from game_timing import BODY_MODES,WARNING_LEAD,INPUT_GRACE,RESPONSE_WINDOW
from main import Engine
from vision_route import camera_event,camera_heartbeat,CameraEvent,CameraHeartbeat,expire_camera
from pose_movements import BodyPose,TwoPlayerTracker
from control_inputs import remote_to_flight
from protocol import LineBuffer
from targeting import DISCOVERIES

def advance(g,seconds):
    for _ in range(round(seconds*100)):g.tick(.01)

def mission(mode='SURFACE_RUN',planet='MARS'):
    g=FlightGame();g.planet=planet;g.mission=local_mission(planet,mode);g.start_mission();return g

@pytest.mark.parametrize('mode',sorted(BODY_MODES))
def test_human_timing_and_render_coordinates(mode):
    g=mission(mode,'SATURN' if mode=='RING_RACE' else 'MARS')
    assert len(g.obstacles)==4
    assert all(o['event_at']-o['cue_at']==pytest.approx(WARNING_LEAD) for o in g.obstacles)
    assert all(2.5<=b['event_at']-a['event_at']<=3.5 for a,b in zip(g.obstacles,g.obstacles[1:]))
    assert g.obstacles[-1]['event_at']+INPUT_GRACE<15
    for o in g.obstacles:
        assert o['z']==o['event_at']*g.snapshot()['timing']['track_speed']

@pytest.mark.parametrize('offset',[-.75,-.3,.15])
def test_jump_response_window_independent_of_player(offset):
    g=mission();at=g.obstacles[0]['event_at'];advance(g,at+offset)
    g.command('FLIGHT,P2,JUMP',source='vision');advance(g,1)
    assert g.players[1]['health']==100 and g.players[1]['score']==10
    assert g.players[0]['health']==92 and g.players[0]['score']==0

def test_late_jump_does_not_rewrite_result():
    g=mission();advance(g,4.1);g.command('FLIGHT,P1,JUMP',source='vision')
    assert g.players[0]['health']==92 and g.players[0]['score']==0

def test_keyboard_focus_release_does_not_cancel_camera_duck():
    g=mission();g.command('FLIGHT,P1,DUCK_ON',source='vision')
    g.command('FLIGHT,P1,DUCK_ON',source='keyboard');g.command('FLIGHT,P1,DUCK_OFF',source='keyboard')
    assert g.players[0]['duck'] and not g.players[1]['duck']
    g.command('FLIGHT,P1,DUCK_OFF',source='vision');assert not g.players[0]['duck']

def test_countdown_does_not_consume_active_seconds_and_carries_duck():
    g=mission();g.transition('BRIEFING');g.command('FLIGHT,P1,SELECT')
    g.command('FLIGHT,P2,DUCK_ON',source='vision');advance(g,2.9)
    assert g.phase=='COUNTDOWN'
    advance(g,.15);assert g.phase=='MISSION' and g.age<.1 and g.players[1]['duck']
    advance(g,14.8);assert g.phase=='MISSION'
    advance(g,.3);assert g.phase=='RESULTS'

def test_camera_http_queue_consumer_collision_and_disconnect(monkeypatch):
    monkeypatch.setenv('SIMULATE_PICO','false')
    async def run():
        e=Engine();e.flight=mission();g=e.flight
        request=SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'),app=SimpleNamespace(state=SimpleNamespace(engine=e)))
        task=asyncio.create_task(e.consume())
        try:
            advance(g,3.3)
            await camera_event(CameraEvent(player='P2',action='JUMP'),request)
            await asyncio.sleep(.01);advance(g,.8)
            assert g.players[1]['score']==10 and g.players[0]['score']==0
            await camera_event(CameraEvent(player='P1',action='DUCK_ON'),request)
            await asyncio.sleep(.01)
            assert g.players[0]['duck'] and not g.players[1]['duck']
            expire_camera(e,e.external_camera_last+4)
            await asyncio.sleep(.01);assert not g.players[0]['duck']
            assert not task.done()
        finally:
            task.cancel();await asyncio.gather(task,return_exceptions=True)
    asyncio.run(run())

def test_camera_heartbeat_repairs_a_dropped_duck_release():
    async def run():
        e=Engine();e.flight=mission();request=SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'),app=SimpleNamespace(state=SimpleNamespace(engine=e)))
        task=asyncio.create_task(e.consume())
        try:
            e.flight.command('FLIGHT,P1,DUCK_ON',source='vision')
            await camera_heartbeat(CameraHeartbeat(ready=True,ducks=[False,False]),request)
            await asyncio.sleep(.01);assert not e.flight.players[0]['duck']
        finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
    asyncio.run(run())

def test_weak_pose_expires_held_duck_and_one_frame_spike_does_not_jump():
    t=TwoPlayerTracker(calibration_frames=4)
    standing=lambda x:BodyPose(x,.3,.6,176,.95)
    for i in range(4):t.process([standing(.2),standing(.8)],i*.05)
    assert t.process([BodyPose(.2,.15,.5,176,.95),standing(.8)],1)==[]
    assert t.process([standing(.2),standing(.8)],1.1)==[]
    t.detectors[0].ducking=True
    t.process([BodyPose(.2,.4,.7,100,.1),standing(.8)],2)
    assert not t.detectors[0].ducking and not t.visible[0]

def test_player_identity_survives_lean_across_center():
    t=TwoPlayerTracker(calibration_frames=3)
    for i in range(3):t.process([BodyPose(.4,.3,.6,176),BodyPose(.8,.3,.6,176)],i*.1)
    t.process([BodyPose(.49,.3,.6,176),BodyPose(.8,.3,.6,176)],.4)
    t.process([BodyPose(.54,.3,.6,176),BodyPose(.8,.3,.6,176)],.5)
    assert t.positions==[.54,.8] and t.ready
    assert t.player_at(.54)==0

def test_remote_snapshot_keeps_tilt_separate_from_joystick():
    g=mission('SAMPLE_HUNT');g.command(remote_to_flight('REMOTE,P1,STATE,1,-1,0.6'),source='remote')
    assert g.active_axes()[0]==[.6,0]
    g.mission=local_mission('MARS','ASTEROID_DODGE');assert g.active_axes()[0]==[-1,0]
    g.transition('NAVIGATION');assert g.active_axes()[0]==[1,-1]
    g.command(remote_to_flight('REMOTE,P2,STATE,0,1,-.7'),source='remote')
    assert g.active_axes()[1]==[0,-.7]
    g.command(remote_to_flight('REMOTE,P1,DISCONNECTED'),source='remote');assert g.active_axes()[0]==[0,0]

def test_usb_chunks_and_camera_events_share_authority():
    async def run():
        e=Engine();e.flight=mission();task=asyncio.create_task(e.consume());buf=LineBuffer()
        try:
            for chunk in (b'REMOTE,P1,STA',b'TE,0,1,0\nREMOTE,P2,STATE,0,-1,0\n'):
                for line in buf.feed(chunk):e.submit('line',line)
            e.submit('input','INPUT,P2,JUMP');await asyncio.sleep(.01)
            assert e.flight.players[1]['jump']>0 and not e.flight.players[0]['jump']
            assert e.flight.remote_axes==[[0,1],[0,-1]]
        finally:task.cancel();await asyncio.gather(task,return_exceptions=True)
    asyncio.run(run())

def test_selected_discovery_is_same_for_remote_and_screen():
    g=FlightGame();g.transition('NAVIGATION');g.ship=[-105,14,-20];g.travel=50
    item=next(d for d in DISCOVERIES if d['id']=='iss')
    g.ship=[item['position'][0],14,item['position'][2]+20]
    dx,dy,dz=[x-y for x,y in zip(item['position'],g.ship)]
    g.players[0]['yaw']=math.atan2(dx,-dz);g.players[0]['pitch']=math.atan2(dy,math.hypot(dx,dz))
    selected=g.snapshot()['selection'];assert selected['id']=='iss'
    g.command('FLIGHT,P1,SELECT',source='remote');assert g.inspected=='iss' and g.phase=='NAVIGATION'
    g.players[0]['yaw']+=math.pi;assert (g.snapshot()['selection'] or {}).get('id')!='iss'

def test_sample_decoys_and_slalom_have_distinct_scoring():
    g=mission('SAMPLE_HUNT');o=g.obstacles[1];g.age=o['event_at']-.4;g.players[0]['x']=o['x'];g.players[0]['score']=25
    g.command('FLIGHT,P1,PRESS');assert g.players[0]['score']==20 and g.players[0]['samples']==0
    g=mission('ORBIT_SLALOM');o=g.obstacles[0];g.players[1]['x']=o['x'];g.players[0]['x']=o['x']+3
    advance(g,o['event_at']+.3);assert g.players[1]['score']==15 and g.players[0]['score']==0

def test_total_scores_added_once_and_no_post_round_actions():
    g=mission();g.obstacles=[];g.players[0]['score']=25;advance(g,15.1)
    assert g.total_scores==[25,0]
    g.command('FLIGHT,P1,JUMP');advance(g,2);assert g.total_scores==[25,0]

def test_rate_limit_respects_retry_delay(monkeypatch):
    import gemini_runtime as runtime
    monkeypatch.setattr(runtime,'blocked_until',0.)
    runtime.record_failure(SimpleNamespace(code=429,details=[{'retryDelay':'120s'}],response=None))
    assert 119<runtime.cooldown_remaining()<=120

def test_controller_telemetry_signs_staleness_and_p2_mapping(monkeypatch):
    monkeypatch.setenv('P1_FORWARD_SIGN','-1')
    g=FlightGame();g.phase='NAVIGATION'
    g.command(remote_to_flight('REMOTE,P1,STATE,0.6,-0.3,0.2'),source='remote')
    g.command(remote_to_flight('REMOTE,P2,STATE,0.4,0.7,-0.5'),source='remote')
    g.command('FLIGHT,P1,AXIS,0,0')
    s=g.snapshot()['controllers']
    assert s[0]['raw']==[.6,-.3,.2] and s[0]['effective']==[-.6,-.3]
    assert s[1]['effective']==[0.,-.5] and s[1]['raw'][1]==.7
    g.command('FLIGHT,P2,SHAKE',source='remote')
    assert g.snapshot()['controllers'][1]['last_action']=='SHAKE'
    advance(g,.41)
    assert not g.snapshot()['controllers'][0]['fresh'] and g.active_axes()[0]==[0.,0.]
    g.command(remote_to_flight('REMOTE,P1,STATE,0,0,0'),source='remote')
    assert g.snapshot()['controllers'][0]['fresh']

def test_no_quizzes_in_any_planet_rotation():
    from flight_game import PLANET_FACTS,eligible_gemini_modes,choose_mode
    for planet in PLANET_FACTS:
        assert 'SCIENCE_QUIZ' not in eligible_gemini_modes(planet)
        assert choose_mode(planet)!='SCIENCE_QUIZ'
        with pytest.raises(ValueError):eligible_gemini_modes(planet,forced_mode='SCIENCE_QUIZ')

def test_camera_start_refuses_remote_origin_and_missing_model(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from vision_route import router
    import download_pose_model
    app=FastAPI();app.include_router(router);app.state.engine=Engine()
    client=TestClient(app,client=('127.0.0.1',1234))
    assert client.post('/api/vision/start',headers={'origin':'https://example.com'}).status_code==403
    monkeypatch.setattr(download_pose_model,'MODEL_PATH',tmp_path/'missing.task')
    response=client.post('/api/vision/start')
    assert response.status_code==409 and 'model missing' in response.json()['detail']

@pytest.mark.parametrize('mode,planet', [('SURFACE_RUN','MARS'),('RING_RACE','SATURN'),('CRATER_LEAP','MARS'),('STORM_SHELTER','MARS')])
def test_uncalibrated_shoulders_reach_mission(mode,planet):
    from pose_movements import MovementDetector
    g=mission(mode,planet)
    detector=MovementDetector(shoulder_only=True)
    assert detector.update(BodyPose(.25,.4,.7,90),0)==[]
    assert detector.ready
    action='DUCK_ON' if mode=='STORM_SHELTER' else 'JUMP'
    y=.53 if action=='DUCK_ON' else .27
    hazard=next(o for o in g.obstacles if o['kind'] in ('STORM',) if mode=='STORM_SHELTER') if mode=='STORM_SHELTER' else g.obstacles[0]
    advance(g,hazard['event_at']-.45)
    events=[]
    for n in range(12):events+=detector.update(BodyPose(.25,y,.7,90),.05+n*.03)
    assert action in events
    for event in events:g.command('FLIGHT,P1,'+event,source='vision')
    advance(g,.7)
    assert g.players[0]['score']>g.players[1]['score']
    assert not g.players[1]['duck']

def test_shoulders_duck_release_and_jitter_without_calibration():
    from pose_movements import MovementDetector
    d=MovementDetector(shoulder_only=True);d.update(BodyPose(.3,.4,.7,90),0)
    events=[]
    for n in range(20):events+=d.update(BodyPose(.3,.4+(.003 if n%2 else -.003),.7,90),n*.03)
    assert not events
    for n in range(12):events+=d.update(BodyPose(.3,.55,.7,90),1+n*.03)
    assert events==['DUCK_ON']
    for n in range(20):events+=d.update(BodyPose(.3,.4,.7,90),2+n*.03)
    assert events==['DUCK_ON','DUCK_OFF']
