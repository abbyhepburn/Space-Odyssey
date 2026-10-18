import asyncio
import pytest
from flight_game import FlightGame,local_mission,choose_mode,MOVES,GameMission,SURFACE_MODES,ROCKY_PLANETS

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
    g.command('FLIGHT,P1,AXIS,1,1');g.command('FLIGHT,P2,AXIS,0,1');advance(g,.2)
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
        assert g.mission.time_limit_s==15 and 1<=len(g.mission.movements)<=2
        g.command('FLIGHT,P1,SELECT');assert g.phase=='COUNTDOWN'
        advance(g,3.05);assert g.phase=='MISSION' and g.age<.1
        g.command('FLIGHT,RESET');assert g.phase=='READY' and g.mission is None
        assert len(g.history['SATURN'])==1
    asyncio.run(run())

def test_each_game_simple_and_context_validated():
    for mode in MOVES:
        planet='MARS' if mode in SURFACE_MODES else 'SATURN'
        m=local_mission(planet,mode).validate_planet(planet,mode)
        assert m.time_limit_s==15 and len(m.movements)<=2
    m=local_mission('SATURN','RING_RACE')
    with pytest.raises(ValueError):m.validate_planet('MARS')
    raw=m.model_dump();raw['time_limit_s']=60
    with pytest.raises(ValueError):GameMission.model_validate(raw)

def test_hurdle_hits_individual_health_and_score():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN','RING_RACE');g.start_mission();g.obstacles[0]['event_at']=.05
    g.command('FLIGHT,P1,JUMP');advance(g,.3)
    assert g.players[0]['health']==100 and g.players[1]['health']==92 and g.players[0]['score']==10 and g.players[1]['score']==0

def test_sync_optional_two_players_and_refractory():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','METEOR_BREAK');g.start_mission();g.mission.sync_boost=True;g.obstacles=[];g.world_time=10
    g.command('FLIGHT,P1,SHAKE');assert g.boost==0
    g.command('FLIGHT,P2,SHAKE');assert g.boost>0 and g.team_score==16
    advance(g,.4);g.command('FLIGHT,P1,SHAKE');g.command('FLIGHT,P2,SHAKE');assert g.team_score==16

def test_finish_declares_individual_winner():
    g=FlightGame();g.planet='SATURN';g.mission=local_mission('SATURN','RING_RACE');g.start_mission()
    g.obstacles=[];g.players[0]['score']=40;g.players[1]['score']=20
    g.age=14.99;g.tick(.05);assert g.phase=='RESULTS' and g.winner=='P1' and g.team_score==60

def test_variety_avoids_last_two():
    recent=[]
    for _ in range(12):
        m=choose_mode('MARS',recent)
        assert m not in recent[-2:] and m!='RING_RACE'
        recent.append(m)

def test_expiry_15_seconds():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS');g.start_mission();g.age=14.99
    g.tick(.02);assert g.phase=='RESULTS'


def test_pilot_turn_and_helm_level_are_separate():
    g=FlightGame();g.transition('NAVIGATION')
    g.command('FLIGHT,P1,AXIS,0,1');advance(g,.2)
    assert g.players[0]['yaw']>0 and g.ship[1]==14 and g.ship[2]==0
    yaw=g.players[0]['yaw']
    g.command('FLIGHT,P1,AXIS,0,0');g.command('FLIGHT,P2,AXIS,1,-1');advance(g,.2)
    assert g.players[0]['yaw']==yaw and g.roll>0 and g.ship[1]==14


def test_every_planet_selectable_and_wraparound():
    import math
    g=FlightGame();assert {t['planet'] for t in g.targets()}=={'MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE'}
    for t in g.targets():
        x,y,z=t['position'];g.ship=[x,y,z+35];g.travel=50
        g.players[0]['yaw']=2*math.pi;g.players[0]['pitch']=0
        assert g.target()==t['planet']


@pytest.mark.parametrize('mode',list(MOVES))
def test_both_players_have_primary_controls(mode):
    planet='MARS' if mode in SURFACE_MODES else 'SATURN'
    g=FlightGame();g.planet=planet;g.mission=local_mission(planet,mode);g.start_mission()
    if 'STEER' in MOVES[mode] or 'TILT' in MOVES[mode]:
        g.command('FLIGHT,P1,AXIS,-1,0');g.command('FLIGHT,P2,AXIS,1,0');advance(g,.2)
        if mode=='SCIENCE_QUIZ':
            assert g.players[0]['selection']==0 and g.players[1]['selection']==2
        else: assert g.players[0]['x']<0<g.players[1]['x']
    if any(c in MOVES[mode] for c in ['SHAKE','PRESS']) and mode!='SCIENCE_QUIZ':
        action='PRESS' if 'PRESS' in MOVES[mode] else 'SHAKE'
        g.mission.sync_boost=False
        g.age=g.obstacles[0]['event_at']-.5
        for p in g.players:p['x']=g.obstacles[0]['x']
        for player in ['P1','P2']:g.command(f'FLIGHT,{player},{action}')
        assert g.obstacles[0]['destroyed_by']==[True,True] and [p['score'] for p in g.players]==[25,25]
    if 'JUMP' in MOVES[mode]:
        for player in ['P1','P2']:
            g.command(f'FLIGHT,{player},JUMP')
            if 'DUCK' in MOVES[mode]:g.command(f'FLIGHT,{player},DUCK_ON')
        assert all(p['jump']>0 for p in g.players)
    if 'FLICK' in MOVES[mode]:
        for player in ['P1','P2']:g.command(f'FLIGHT,{player},UPWARD_FLICK')
        assert all(p['flick']>0 for p in g.players)
    if 'DUCK' in MOVES[mode]:
        for player in ['P1','P2']:g.command(f'FLIGHT,{player},DUCK_ON')
        assert all(p['duck'] for p in g.players)


def test_continue_exploration_retains_location():
    g=FlightGame();g.ship=[70,20,-100];g.phase='RESULTS';g.command('FLIGHT,EXPLORE')
    assert g.phase=='NAVIGATION' and g.ship==[70,20,-100]


def test_surface_modes_only_generated_for_rocky_planets():
    for _ in range(50):
        assert choose_mode('SATURN') not in SURFACE_MODES
    for planet in ROCKY_PLANETS:
        for mode in SURFACE_MODES:
            local_mission(planet,mode).validate_planet(planet,mode)
    with pytest.raises(ValueError):local_mission('JUPITER','SAMPLE_HUNT').validate_planet('JUPITER')


def test_matched_actions_trigger_optional_team_sync_without_shaking():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','CRATER_LEAP');g.start_mission()
    # Two remote upward flicks within the sync window trigger shield + bonus.
    g.mission.sync_boost=True
    g.world_time=8
    g.command('FLIGHT,P1,UPWARD_FLICK');assert g.boost==0
    g.tick(.4);g.command('FLIGHT,P2,UPWARD_FLICK')
    assert g.boost>0 and g.team_score==16
    g.command('FLIGHT,P1,SHAKE');g.command('FLIGHT,P2,SHAKE')
    assert g.team_score==16  # cooldown prevents farming


def test_sync_uses_only_related_mission_action():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','SURFACE_RUN');g.start_mission()
    g.mission.sync_boost=True
    g.world_time=3
    g.command('FLIGHT,P1,SHAKE');g.command('FLIGHT,P2,SHAKE')
    assert g.boost==0 and g.team_score==0  # unrelated movement cannot trigger bonus
    g.command('FLIGHT,P1,JUMP');g.command('FLIGHT,P2,JUMP')
    assert g.boost>0 and g.team_score==16


def test_optional_sync_can_be_disabled():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','CRATER_LEAP');g.mission.sync_boost=False;g.start_mission()
    g.world_time=4
    g.command('FLIGHT,P1,UPWARD_FLICK');g.command('FLIGHT,P2,UPWARD_FLICK')
    assert g.boost==0 and g.team_score==0


def test_final_timed_events_reach_last_second():
    for mode in MOVES:
        planet='MARS' if mode in SURFACE_MODES else 'SATURN'
        g=FlightGame();g.planet=planet;g.mission=local_mission(planet,mode);g.start_mission()
        event_times=[o['event_at'] for o in g.obstacles]
        assert len(event_times)==(5 if mode=='SCIENCE_QUIZ' else g.mission.obstacle_count)
        assert .5<=event_times[0]<=3.8 and event_times[-1]>=(13 if mode=='SCIENCE_QUIZ' else 14-1e-8)
        assert all(a<b for a,b in zip(event_times,event_times[1:]))
        advance(g,13.5)
        assert g.phase=='MISSION' and any(not o['passed'][0] for o in g.obstacles)
        advance(g,1.6)
        assert g.phase=='RESULTS' and all(o['passed'][0] or o['destroyed_by'][0] for o in g.obstacles)

def test_player_two_wins_and_ties_are_possible():
    for scores,winner in [([8,25],'P2'),([10,10],'TIE')]:
        g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS');g.start_mission()
        g.obstacles=[]
        for player,score in zip(g.players,scores):player['score']=score
        advance(g,15.1)
        assert g.winner==winner

def test_mission_planet_fact_present():
    g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS');g.start_mission()
    assert 'dust' in g.snapshot()['education']['fact'].lower()

def test_mission_mode_objectives_are_distinct():
    for mode,types in {'CRATER_LEAP':{'PIT','RIDGE'},'SAMPLE_HUNT':{'SAMPLE'},'STORM_SHELTER':{'GENERATOR','STORM'}}.items():
        g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS',mode);g.start_mission()
        assert {o['kind'] for o in g.obstacles}==types
        assert len(g.mission.movements)==2

# Additional coverage for the education-based variety update.

def test_rotation_prevents_cross_planet_looping():
    from flight_game import choose_mode
    recent=[]
    for planet in ['JUPITER','NEPTUNE','URANUS','SATURN'] * 4:
        mode=choose_mode(planet,global_recent=recent)
        assert mode not in recent[-4:], f'{mode} repeated too soon across planets'
        recent.append(mode)


def test_only_standard_game_rules_are_allowed():
    from flight_game import choose_style
    assert choose_style(('STANDARD',))=='STANDARD'
    m=local_mission('MARS','SAMPLE_HUNT')
    assert m.challenge_style=='STANDARD'
    with pytest.raises(ValueError):
        local_mission('MARS','SAMPLE_HUNT','PRECISION')


def test_relay_repair_uses_only_future_remote_actions():
    g=FlightGame();g.planet='NEPTUNE';g.mission=local_mission('NEPTUNE','RELAY_REPAIR');g.start_mission()
    assert [m.control for m in g.mission.movements]==['TILT','SHAKE']
    g.mission.sync_boost=False
    g.obstacles[0]['x']=0.;g.obstacles[0]['event_at']=1.0
    g.age=.35
    g.command('FLIGHT,P1,SHAKE')
    assert g.obstacles[0]['destroyed_by'][0] and not g.obstacles[0]['destroyed_by'][1]
    assert g.players[0]['chargers']==1 and g.players[0]['score']==25


def test_gemini_game_pattern_changes_actual_lane_order():
    g=FlightGame();g.planet='JUPITER';g.mission=local_mission('JUPITER','BEACON_RELAY')
    g.mission.event_pattern='ALTERNATING';g.start_mission()
    assert [o['x'] for o in g.obstacles[:4]]==[-2.7,2.7,-2.7,2.7]


def test_science_card_and_implemented_mode():
    from flight_game import MODE_LESSONS
    g=FlightGame();g.planet='JUPITER';g.mission=local_mission('JUPITER','RELAY_REPAIR')
    education=g.snapshot()['education']
    assert 'Great Red Spot' in education['fact']
    assert education['why']==MODE_LESSONS['RELAY_REPAIR']
    assert 'challenge' not in education


def test_revisits_get_distinct_verified_fact_cards():
    from flight_game import choose_planet_fact,EXTRA_PLANET_FACTS
    for planet in EXTRA_PLANET_FACTS:
        recent=[]
        for _ in range(9):
            card=choose_planet_fact(planet,recent)
            assert card['fact'] not in recent[-2:]
            assert card['url'].startswith('https://science.nasa.gov/')
            recent.append(card['fact'])


def test_ai_fallback_preserves_educational_story_and_variety_without_key(monkeypatch):
    from flight_game import generate_game
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    async def run():
        global_recent=[];styles=[];facts=[]
        for _ in range(5):
            lesson=__import__('flight_game').choose_planet_fact('SATURN',facts)
            m,source=await generate_game('SATURN',global_recent=global_recent,style_history=styles,lesson=lesson)
            assert source=='LOCAL · NO API KEY'
            assert m.game_type not in global_recent[-4:] and m.challenge_style=='STANDARD'
            global_recent.append(m.game_type);styles.append(m.challenge_style);facts.append(lesson['fact'])
    asyncio.run(run())


def test_gravity_sling_requires_align_and_flick_and_has_relevant_sync():
    g=FlightGame();g.planet='JUPITER';g.mission=local_mission('JUPITER','GRAVITY_SLING');g.start_mission()
    assert [m.control for m in g.mission.movements]==['STEER','FLICK']
    g.mission.sync_boost=False
    g.obstacles[0]['event_at']=.05;g.obstacles[0]['x']=0
    g.command('FLIGHT,P1,UPWARD_FLICK');advance(g,.3)
    assert g.players[0]['score']==15 and g.players[1]['score']==0
    assert g.players[1]['health']==92
    assert g.snapshot()['education']['why'].startswith('Gravity assists')


def test_analog_forward_thrust_and_f_release():
    """Remote joystick-forward and laptop F share normalized P1 AXIS X."""
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    start=g.ship[:]
    for _ in range(22):
        g.command('FLIGHT,P1,AXIS,0.5,0')
        g.tick(.05)
    assert 15 < g.speed < 18
    assert g.snapshot()['thrust_input']==0.5
    assert g.ship[2] < start[2]-10
    for _ in range(20):
        g.command('FLIGHT,P1,AXIS,0,0')
        g.tick(.05)
    assert g.snapshot()['thrust_input']==0
    assert g.speed < 2
    # A disconnected device must not leave thrust stuck on.
    g.command('FLIGHT,P1,AXIS,1,0')
    g.tick(.05)
    advance(g,1.0)
    assert g.snapshot()['thrust_input']==0
    assert g.speed < 2


def test_ground_mission_is_directly_requestable_on_rocky_planets(monkeypatch):
    import asyncio
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    async def run():
        g=FlightGame();g.planet='MARS';g.mission=local_mission('MARS','METEOR_BREAK');g.transition('BRIEFING')
        g.command('FLIGHT,SURFACE_GAME')
        assert g.phase=='GENERATING'
        await g.task
        assert g.mission.game_type=='SURFACE_RUN'
        assert g.mission.time_limit_s==15
        g.transition('BRIEFING')
        g.command('FLIGHT,SURFACE_GAME');await g.task
        assert g.mission.game_type=='CRATER_LEAP'
        giant=FlightGame();giant.planet='JUPITER';giant.transition('BRIEFING')
        giant.command('FLIGHT,SURFACE_GAME')
        assert giant.phase=='GENERATING'
        await giant.task
        assert giant.mission.game_type=='ORBIT_SLALOM'
    asyncio.run(run())


def test_reverse_throttle_moves_ship_backwards_and_stops():
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    initial_z=g.ship[2]
    for _ in range(20):
        g.command('FLIGHT,P1,AXIS,-1,0');g.tick(.05)
    assert g.speed < -20
    assert g.ship[2] > initial_z  # ship travels backwards relative to forward heading
    assert g.snapshot()['reverse_input']==1
    for _ in range(15):
        g.command('FLIGHT,P1,AXIS,0,0');g.tick(.05)
    assert abs(g.speed)<1
    assert g.snapshot()['throttle_input']==0


def test_p1_steers_ship_and_p2_only_stabilizes_roll():
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    start_yaw=g.players[0]['yaw'];start_roll=g.roll
    for _ in range(12):
        g.command('FLIGHT,P2,AXIS,1,-1');g.tick(.05)
    assert g.players[0]['yaw']==start_yaw
    assert g.roll>start_roll
    for _ in range(12):
        g.command('FLIGHT,P1,AXIS,0,-1');g.tick(.05)
    assert g.players[0]['yaw'] < start_yaw - .2
    assert g.players[1]['yaw'] == g.players[0]['yaw']


def test_reversing_after_forward_thrust_changes_signed_speed():
    g=FlightGame();g.command('FLIGHT,LAUNCH');advance(g,5.1)
    for _ in range(12):
        g.command('FLIGHT,P1,AXIS,1,0');g.tick(.05)
    assert g.speed>0
    for _ in range(20):
        g.command('FLIGHT,P1,AXIS,-1,0');g.tick(.05)
    assert g.speed<0
