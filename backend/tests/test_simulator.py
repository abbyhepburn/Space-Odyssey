from simulator import Simulator

def race():
    s=Simulator();s.tick(8999);assert s.state.phase=='CUTSCENE'
    s.tick(1);assert s.state.phase=='COUNTDOWN'
    s.tick(3000);assert s.state.phase=='RACE'
    return s

def test_complete_race_and_restart():
    s=race()
    s.command('INPUT,P1,JUMP');assert s.state.p1_pose=='JUMP'
    s.tick(700);assert s.state.p1_pose=='NORMAL'
    s.command('INPUT,P2,DUCK_ON');assert s.state.p2_pose=='DUCK'
    s.command('INPUT,P2,DUCK_OFF');assert s.state.p2_pose=='NORMAL'
    s.command('INPUT,P2,RUN')
    for _ in range(100): s.command('INPUT,P1,RUN');s.tick(150)
    assert s.state.phase=='RESULTS' and s.state.winner=='P1'
    s.command('RESET');assert s.state.phase=='CUTSCENE' and s.state.score1==0

def test_phase_capabilities_ack_and_completion():
    s=Simulator()
    assert 'REJECTED' in s.command('SET_MISSION,SATURN_JUMP,3,40')[0]
    s=race();s.command('CAPABILITIES,0,0')
    assert 'NOT_READY' in s.command('SET_MISSION,SATURN_JUMP,3,40')[0]
    assert 'MISSION_ACCEPTED' in s.command('SET_MISSION,SATURN_SPRINT,4,15')[0]
    assert 'BUSY' in s.command('SET_MISSION,SATURN_SPRINT,4,15')[0]
    completed=[]
    for _ in range(4): completed+=s.command('INPUT,P1,RUN');s.tick(150)
    assert 'MISSION_COMPLETED,SATURN_SPRINT,P1' in completed
    assert s.state.progress1==4
    s.tick(15000);assert s.state.mission_id=='NONE'

def test_duck_transitions_only():
    s=race();s.command('SET_MISSION,SATURN_DUCK,3,40')
    for _ in range(10): s.command('INPUT,P1,DUCK_ON')
    assert s.state.progress1==1
    s.command('INPUT,P1,DUCK_OFF');s.command('INPUT,P1,DUCK_ON')
    assert s.state.progress1==2

def test_timer_tie():
    s=race();s.tick(120000);assert s.state.phase=='RESULTS' and s.state.winner=='TIE'
