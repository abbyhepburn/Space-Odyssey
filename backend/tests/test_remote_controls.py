import pytest
from flight_game import FlightGame
from control_inputs import remote_to_flight
from main import Engine


def test_remote_normalization():
    assert remote_to_flight('REMOTE,P1,AXIS,0.7,-0.5') == 'FLIGHT,P1,AXIS,0.7,-0.5'
    assert remote_to_flight('REMOTE,P2,SHAKE') == 'FLIGHT,P2,SHAKE'
    assert remote_to_flight('REMOTE,P1,SELECT') == 'FLIGHT,P1,SELECT'
    for bad in ['REMOTE,P3,SELECT','REMOTE,P1,AXIS,nan,0','REMOTE,P1,AXIS,2,0',
                'REMOTE,P1,AXIS,1','REMOTE,P2,BAD','REMOTE,P1,AXIS,0,inf',
                'REMOTE,P1,AXIS,0,0,0']:
        with pytest.raises(ValueError): remote_to_flight(bad)


def test_physical_remote_overrides_idle_keyboard_and_keeps_fallback():
    g=FlightGame(simulated=False)
    g.transition('NAVIGATION')
    g.ship=[0.,0.,-100.]  # Avoid Earth's launch safety zone.
    g.command('FLIGHT,P1,AXIS,0,0',source='keyboard')
    g.command(remote_to_flight('REMOTE,P1,AXIS,1,-0.3'),source='remote')
    for _ in range(4):
        g.command('FLIGHT,P1,AXIS,0,0',source='keyboard')
        g.tick(.05)
    assert g.speed>0 and g.players[0]['yaw']<0
    assert g.snapshot()['throttle_input']==1
    # Remote timing out hands input back to the live keyboard source.
    for _ in range(12):
        g.command('FLIGHT,P1,AXIS,-1,1',source='keyboard')
        g.tick(.05)
    assert g.snapshot()['throttle_input']==-1
    assert g.speed<0
    assert g.players[0]['yaw']>-.1


def test_keyboard_and_remote_are_accepted_by_same_backend_engine():
    e=Engine()
    e.flight.transition('NAVIGATION')
    e.control('FLIGHT,P1,AXIS,1,0')
    e.flight.tick(.05)
    assert e.flight.speed>0
    e.control('REMOTE,P1,AXIS,-1,0')
    e.flight.tick(.05)
    assert e.flight.snapshot()['throttle_input']==-1


def test_remote_p1_yaw_p2_only_roll():
    g=FlightGame(simulated=False)
    g.transition('NAVIGATION')
    g.command(remote_to_flight('REMOTE,P1,AXIS,0,1'),source='remote')
    g.command(remote_to_flight('REMOTE,P2,AXIS,0,1'),source='remote')
    g.tick(.2)
    assert g.players[0]['yaw']>0
    assert g.players[0]['yaw']==g.players[1]['yaw']
    assert g.roll<0


def test_centered_controllers_hold_ship_heading_and_roll_without_spin():
    g=FlightGame();g.transition('NAVIGATION');g.roll=.12
    g.players[0]['yaw']=.45;g.players[1]['yaw']=.45
    start=list(g.ship)
    for _ in range(400):
        g.command('FLIGHT,P1,AXIS,0,0');g.command('FLIGHT,P2,AXIS,0,0')
        g.tick(.05)
    assert g.roll==.12 and g.players[0]['yaw']==pytest.approx(.45)
    assert g.ship==start and g.speed==0


def test_roll_stops_changing_when_controller_returns_to_center():
    g=FlightGame();g.transition('NAVIGATION')
    g.command('FLIGHT,P2,AXIS,0,1');g.tick(.2)
    assert g.roll<0
    g.command('FLIGHT,P2,AXIS,0,0');held=g.roll
    for _ in range(40):g.tick(.05)
    assert g.roll==held


def test_p2_tilt_ramps_smoothly_and_neutral_stops_without_drift():
    g=FlightGame();g.transition('NAVIGATION')
    g.command('FLIGHT,P2,SENSORS,0,0,1',source='remote')
    g.tick(1/60)
    assert 0 < g.roll_input < .2
    first=g.roll
    g.tick(.1)
    assert .5 < g.roll_input < 1
    assert g.roll < first < 0
    g.command('FLIGHT,P2,SENSORS,0,0,-1',source='remote')
    before=g.roll_input;g.tick(1/60)
    assert -1 < g.roll_input < before
    g.command('FLIGHT,P2,SENSORS,0,0,0',source='remote')
    held=g.roll;g.tick(.2)
    assert g.roll_input==0 and g.roll==held


def test_p1_turning_matches_github_response_and_release_holds_heading():
    import math
    g=FlightGame();g.transition('NAVIGATION')
    g.command('FLIGHT,P1,AXIS,0,1');g.tick(.1)
    assert g.players[0]['yaw']==pytest.approx(.065)
    g.command('FLIGHT,P1,AXIS,0,-1');g.tick(.1)
    assert g.players[0]['yaw']==pytest.approx(0.)
    g.command('FLIGHT,P1,AXIS,0,.25');g.tick(.1)
    assert g.players[0]['yaw']==pytest.approx(.01625)
    g.command('FLIGHT,P1,AXIS,0,0')
    heading=g.players[0]['yaw'];g.tick(.2)
    assert g.players[0]['yaw']==pytest.approx(heading)
    g.players[0]['yaw']=math.pi-.01
    g.command('FLIGHT,P1,AXIS,0,1');g.tick(.1)
    assert g.players[0]['yaw']==pytest.approx(-math.pi+.055)


def test_physical_usb_event_reaches_flight_authority():
    import asyncio
    async def scenario():
        e=Engine()
        e.flight.transition('NAVIGATION')
        e.flight.ship=[0.,0.,-100.]
        task=asyncio.create_task(e.consume())
        e.submit('line','REMOTE,P1,AXIS,0.6,0.4')
        e.submit('line','REMOTE,P2,AXIS,0,-0.6')
        await asyncio.sleep(.01)
        e.flight.tick(.1)
        assert e.flight.snapshot()['throttle_input']==.6
        assert e.flight.players[0]['yaw']>0
        assert e.flight.roll>0
        e.submit('line','REMOTE,P1,AXIS,nan,0')
        await asyncio.sleep(.01)
        assert e.status['message']=='Ignored invalid remote event'
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
    asyncio.run(scenario())
