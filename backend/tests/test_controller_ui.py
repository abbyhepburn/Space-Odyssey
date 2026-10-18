import asyncio
import time
import pytest
from main import Engine
from flight_game import local_mission, DESTINATIONS
from control_inputs import remote_to_flight


def test_controller_click_cannot_launch_under_manual():
    e=Engine();e.control('UI,CONTEXT,MODAL')
    for p in ('P1','P2'):e.control(f'REMOTE,{p},SELECT')
    assert e.flight.phase=='READY'
    assert e.snapshot()['flight']['ui_presses']==[1,1]
    e.control('UI,CONTEXT,GAME');e.control('FLIGHT,LAUNCH')
    assert e.flight.phase=='BOOT'


def test_modal_neutralizes_game_axes_but_keeps_live_sensor_data():
    e=Engine();e.flight.transition('NAVIGATION');e.control('UI,CONTEXT,MODAL')
    e.control('REMOTE,P1,STATE,1,-1,0.7')
    e.control('REMOTE,P1,MPU,1,1.2,2.3,9.81,0.1,0.2,0.3')
    row=e.snapshot()['flight']['controllers'][0]
    assert row['raw']==[1,-1,.7] and row['effective']==[0,0]
    assert row['mpu']['fresh'] and row['mpu']['accel']==[1.2,2.3,9.81]
    e.control('UI,CONTEXT,GAME')
    assert e.flight.active_axes()[0]==[1,-1]


def test_ui_handles_results_without_replaying_button_in_next_phase():
    e=Engine();e.flight.planet='MARS';e.flight.transition('RESULTS')
    e.control('UI,CONTEXT,GAME');e.control('REMOTE,P2,SELECT')
    assert e.flight.phase=='RESULTS' and e.ui_presses==[0,1]
    e.control('FLIGHT,EXPLORE')
    mars=next(t for t in DESTINATIONS if t[0]=='MARS')
    assert e.flight.phase=='NAVIGATION' and e.flight.ship==[mars[1],mars[2],mars[3]+65]
    assert e.flight.target() is None  # Face away; cannot immediately re-enter.


def test_mission_controller_button_still_scores_and_modal_button_does_not():
    e=Engine();g=e.flight;g.planet='MARS';g.mission=local_mission('MARS','SAMPLE_HUNT');g.start_mission()
    e.control('UI,CONTEXT,GAME')
    # Both players collect their own copy of an authoritative sample.
    sample=next(o for o in g.obstacles if o['kind']=='SAMPLE' and o.get('research',True))
    g.age=sample['event_at']-.1
    for p in g.players:p['x']=sample['x']
    e.control('REMOTE,P1,SELECT')
    assert g.players[0]['samples']==1 and g.players[1]['samples']==0
    e.control('UI,CONTEXT,MODAL');e.control('REMOTE,P2,SELECT')
    assert g.players[1]['samples']==0 and e.ui_presses==[0,1]


def test_ui_lease_expires_to_legacy_remote_control():
    e=Engine();e.control('UI,CONTEXT,GAME');e.ui_context_until=time.monotonic()-1
    e.control('REMOTE,P1,SELECT')
    assert e.flight.phase=='BOOT' and e.ui_presses==[0,0]


def test_serial_consumer_uses_ui_routing_and_keeps_mpu_health():
    async def run():
        e=Engine();e.control('UI,CONTEXT,MODAL')
        task=asyncio.create_task(e.consume())
        try:
            e.submit('line','REMOTE,P2,SELECT')
            e.submit('line','REMOTE,P2,MPU,0,0,0,0,0,0,0')
            await asyncio.sleep(.01)
            assert e.ui_presses==[0,1] and e.flight.phase=='READY'
            assert not e.flight.controller_snapshot()[1]['mpu']['ok']
            e.flight.tick(.25);e.flight.tick(.25);e.flight.tick(.01)
            assert not e.flight.controller_snapshot()[1]['mpu']['fresh']
        finally:
            task.cancel();await asyncio.gather(task,return_exceptions=True)
    asyncio.run(run())


@pytest.mark.parametrize('line',['REMOTE,P1,MPU,1,nan,0,0,0,0,0','REMOTE,P2,MPU,2,0,0,0,0,0,0','REMOTE,P1,MPU,1,0,0,0,0,0'])
def test_malformed_telemetry_cannot_poison_game(line):
    with pytest.raises(ValueError):remote_to_flight(line)
