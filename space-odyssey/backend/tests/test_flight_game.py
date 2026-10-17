import asyncio
import pytest
from flight_game import FlightGame,local_mission,generate_game

def advance(g,seconds):
    for _ in range(round(seconds*20)):g.tick(.05)

def test_launch_roles_stale_input():
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    assert g.phase=='NAVIGATION'
    g.command('FLIGHT,P1,AXIS,1,1');g.command('FLIGHT,P2,AXIS,-1,0');advance(g,.2)
    assert g.players[0]['yaw']>0 and g.speed==16
    assert g.players[1]['yaw']==g.players[0]['yaw']
    advance(g,1);yaw=g.players[0]['yaw'];advance(g,.5)
    assert g.players[0]['yaw']==yaw

def test_axis_validation():
    g=FlightGame()
    for value in ['nan','inf','2','-2']:
        with pytest.raises(ValueError):g.command(f'FLIGHT,P1,AXIS,{value},0')

def test_select_generate_brief_mission(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    async def run():
        g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
        assert g.target(0)=='SATURN'
        g.command('FLIGHT,P2,SELECT');assert g.phase=='NAVIGATION'
        g.command('FLIGHT,P1,SELECT');assert g.phase=='TRAVEL'
        await g.task;advance(g,4.1);assert g.phase=='BRIEFING'
        assert 'LOCAL' in g.source and g.mission.game_type=='RING_RACE'
        g.command('FLIGHT,P1,SELECT');assert g.phase=='MISSION' and len(g.obstacles)==8
        g.command('FLIGHT,P1,JUMP');assert g.players[0]['jump']>0
        advance(g,1);assert g.players[0]['jump']==0
        g.command('FLIGHT,RESET');assert g.phase=='READY' and g.mission is None
    asyncio.run(run())

def test_gemini_validation_context():
    m=local_mission('SATURN')
    with pytest.raises(ValueError):m.validate_planet('MARS')
    m.planet='MARS'
    with pytest.raises(ValueError):m.validate_planet('MARS')

def test_hurdle_collision_and_correct_jump():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN');g.start_mission()
    g.obstacles[0]['z']=1
    g.command('FLIGHT,P1,JUMP');advance(g,.1)
    assert g.players[0]['health']==100 and g.players[1]['health']==80

def test_two_player_large_asteroid():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS');g.start_mission();g.world_time=10
    g.obstacles=[dict(id=0,x=0,y=0,z=10,kind='LARGE',destroyed=False,passed=[False,False])]
    g.command('FLIGHT,P1,SHAKE');assert not g.obstacles[0]['destroyed']
    g.command('FLIGHT,P2,SHAKE');assert g.obstacles[0]['destroyed']

def test_finish_awards_winner():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN');g.start_mission()
    g.obstacles=[];g.players[0]['distance']=70+g.mission.obstacle_count*55
    g.tick(.05);assert g.phase=='RESULTS' and g.winner=='P1' and g.players[0]['score']==100
