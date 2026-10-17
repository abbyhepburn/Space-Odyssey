import asyncio
import pytest
from flight_game import FlightGame,local_mission,choose_mode,MOVES,GameMission

def advance(g,seconds):
    for _ in range(round(seconds*20)):g.tick(.05)

def fly(g,seconds=3):
    for _ in range(round(seconds*20)):
        g.command('FLIGHT,P1,AXIS,1,0');g.tick(.05)

def test_thrust_translates_and_selection_requires_approach():
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    assert g.phase=='NAVIGATION' and g.target() is None
    before=g.ship[:];distance=g.targets()[1]['distance'];fly(g)
    assert g.ship[2]<before[2]-50 and g.targets()[1]['distance']<distance and g.target()=='SATURN'
    g.command('FLIGHT,P1,AXIS,1,1');g.command('FLIGHT,P2,AXIS,1,0');advance(g,.2)
    assert g.players[0]['yaw']>0 and g.players[1]['yaw']==g.players[0]['yaw']
    advance(g,3);yaw=g.players[0]['yaw'];advance(g,.5)
    assert g.players[0]['yaw']==yaw and g.speed<1

def test_axis_validation():
    for value in ['nan','inf','2','-2']:
        with pytest.raises(ValueError):FlightGame().command(f'FLIGHT,P1,AXIS,{value},0')

def test_select_brief_mission_and_reset(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    async def run():
        g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1);fly(g)
        g.command('FLIGHT,P2,SELECT');assert g.phase=='NAVIGATION'
        g.command('FLIGHT,P1,SELECT');assert g.phase=='TRAVEL'
        await g.task;advance(g,4.1);assert g.phase=='BRIEFING'
        assert g.mission.time_limit_s==20 and 1<=len(g.mission.movements)<=2
        g.command('FLIGHT,P1,SELECT');assert g.phase=='MISSION'
        g.command('FLIGHT,RESET');assert g.phase=='READY' and g.mission is None
        assert len(g.history['SATURN'])==1
    asyncio.run(run())

def test_each_game_simple_and_context_validated():
    for mode in MOVES:
        m=local_mission('SATURN',mode).validate_planet('SATURN',mode)
        assert m.time_limit_s==20 and len(m.movements)<=2
    m=local_mission('SATURN','RING_RACE')
    with pytest.raises(ValueError):m.validate_planet('MARS')
    raw=m.model_dump();raw['time_limit_s']=60
    with pytest.raises(ValueError):GameMission.model_validate(raw)

def test_hurdle_hits_shared_health_and_scores_team():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN','RING_RACE');g.start_mission();g.obstacles[0]['z']=1
    g.command('FLIGHT,P1,JUMP');advance(g,.1)
    assert g.health==92 and g.team_score==10 and all(p['health']==92 for p in g.players)

def test_sync_optional_two_players_and_refractory():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','ORBIT_SLALOM');g.start_mission();g.world_time=10
    g.command('FLIGHT,P1,SHAKE');assert g.boost==0
    g.command('FLIGHT,P2,SHAKE');assert g.boost>0 and g.team_score==20
    advance(g,.4);g.command('FLIGHT,P1,SHAKE');g.command('FLIGHT,P2,SHAKE');assert g.team_score==20

def test_finish_awards_team():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN','RING_RACE');g.start_mission()
    g.obstacles=[];g.players[0]['distance']=35+g.mission.obstacle_count*24
    g.age=19.99;g.tick(.05);assert g.phase=='RESULTS' and g.winner=='TEAM' and g.team_score==100

def test_variety_avoids_last_two():
    recent=[]
    for _ in range(12):
        m=choose_mode('MARS',recent)
        assert m not in recent[-2:] and m!='RING_RACE'
        recent.append(m)

def test_expiry_20_seconds():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS');g.start_mission();g.age=19.99
    g.tick(.02);assert g.phase=='RESULTS'


def test_pilot_vertical_and_helm_turn_and_tilt_are_separate():
    g=FlightGame();g.transition('NAVIGATION')
    g.command('FLIGHT,P1,AXIS,0,1');advance(g,.2)
    assert g.ship[1]>0 and g.players[0]['yaw']==0 and g.ship[2]==0
    height=g.ship[1]
    g.command('FLIGHT,P1,AXIS,0,0');g.command('FLIGHT,P2,AXIS,1,-1');advance(g,.2)
    assert g.players[0]['yaw']>0 and g.roll>0 and g.ship[1]==height


def test_every_planet_selectable_and_wraparound():
    import math
    g=FlightGame();assert {t['planet'] for t in g.targets()}=={'MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE'}
    for t in g.targets():
        x,y,z=t['position'];g.ship=[x,y,z+100];g.travel=50
        g.players[0]['yaw']=2*math.pi;g.players[0]['pitch']=0
        assert g.target()==t['planet']


@pytest.mark.parametrize('mode',list(MOVES))
def test_both_players_have_primary_controls(mode):
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN',mode);g.start_mission()
    if 'STEER' in MOVES[mode]:
        g.command('FLIGHT,P1,AXIS,-1,0');g.command('FLIGHT,P2,AXIS,1,0');advance(g,.2)
        assert g.players[0]['x']<0<g.players[1]['x']
    if any(c in MOVES[mode] for c in ['SHAKE','PRESS']):
        action='PRESS' if 'PRESS' in MOVES[mode] else 'SHAKE'
        g.mission.sync_boost=False
        for p in g.players:p['x']=g.obstacles[0]['x']
        for player in ['P1','P2']:g.command(f'FLIGHT,{player},{action}')
        assert g.obstacles[0]['destroyed_by']==[True,True] and g.team_score==50
    if 'JUMP' in MOVES[mode]:
        for player in ['P1','P2']:
            g.command(f'FLIGHT,{player},JUMP');g.command(f'FLIGHT,{player},DUCK_ON')
        assert all(p['jump']>0 and p['duck'] for p in g.players)


def test_continue_exploration_retains_location():
    g=FlightGame();g.ship=[70,20,-100];g.phase='RESULTS';g.command('FLIGHT,EXPLORE')
    assert g.phase=='NAVIGATION' and g.ship==[70,20,-100]
