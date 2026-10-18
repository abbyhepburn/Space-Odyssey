import math
from flight_game import FlightGame,local_mission,DESTINATIONS
from control_inputs import remote_to_flight

def advance(g,t):
    for _ in range(round(t*20)):g.tick(.05)

def test_launch_cannot_skip_boot_by_repeated_select():
    g=FlightGame();g.command('FLIGHT,P1,SELECT',source='remote')
    assert g.phase=='BOOT'
    for _ in range(20):
        g.command('FLIGHT,P1,SELECT',source='remote');g.command('FLIGHT,LAUNCH');g.tick(.25)
    assert g.phase=='BOOT'
    advance(g,5.1);assert g.phase=='LAUNCH'
    y=g.ship[1];advance(g,5.1)
    assert g.phase=='NAVIGATION' and g.ship[1]>y

def finish(g,planet,scores):
    g.planet=planet;g.mission=local_mission(planet,'ORBIT_SLALOM');g.start_mission();g.obstacles=[]
    for p,score in zip(g.players,scores):p['score']=score
    g.age=g.mission.time_limit_s-.01;g.tick(.02)

def test_first_scores_survive_replay_and_leave_and_reset():
    g=FlightGame();finish(g,'EARTH',[10,5]);finish(g,'EARTH',[0,100])
    assert g.planet_results['EARTH']=={'scores':[10,5],'winner':'P1'}
    g.command('FLIGHT,P1,SELECT',source='remote')
    earth=next(t for t in DESTINATIONS if t[0]=='EARTH')
    assert g.phase=='NAVIGATION' and math.dist(g.ship,earth[1:])==65
    assert g.planet_results['EARTH']['winner']=='P1'
    g.command('FLIGHT,RESET');assert not g.planet_results

def test_tournament_counts_first_round_wins_only():
    g=FlightGame()
    for i,(planet,*_) in enumerate(DESTINATIONS):finish(g,planet,[10,0] if i<5 else [0,10])
    s=g.snapshot();assert s['expedition_complete'] and s['expedition_wins']==[5,3]

def test_mpu_telemetry_does_not_move_ship_or_replace_gesture():
    g=FlightGame();g.command('FLIGHT,P1,SHAKE',source='remote')
    g.command(remote_to_flight('REMOTE,P1,MPU,1,0,0,9.81,0.2,0,0'),source='remote')
    row=g.controller_snapshot()[0]
    assert row['mpu']['ok'] and row['mpu']['accel'][2]==9.81
    assert row['last_action']=='SHAKE' and row['packets']==0

def test_visual_gravity_bonus_is_capped_and_leaves_timing_alone():
    g=FlightGame()
    for planet,expected in [('EARTH',1),('MARS',1),('JUPITER',1.2295)]:
        g.planet=planet;assert abs(g.snapshot()['jump_scale']-expected)<.001


def test_leave_during_arrival_does_not_award_a_round():
    g=FlightGame();g.planet='MARS';g.transition('ARRIVAL');g.command('FLIGHT,EXPLORE')
    assert g.phase=='NAVIGATION' and not g.planet_results
