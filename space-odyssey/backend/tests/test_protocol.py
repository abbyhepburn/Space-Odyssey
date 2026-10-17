import pytest
from protocol import State, parse_line, command_line, LineBuffer

def test_roundtrip():
    assert parse_line(State().line())['state']==vars(State())
    assert parse_line('STATE,RACE,SATURN,120,110,NORMAL,JUMP,30,20,SATURN_SPRINT,4,6,NONE,15234')['state']['progress2']==6

@pytest.mark.parametrize('line',['debugging...', 'STATE,RACE', State(p1_distance=-1).line(),State(p1_pose='FLY').line(),State(winner='P3').line(),State(mission_id='MARS').line(),State().line()+',extra','HELLO,2,ASTROLAB_PICO'])
def test_bad_frames(line): assert parse_line(line) is None

def test_chunks_and_overflow():
    b=LineBuffer(); assert b.feed(b'HELLO,1,ASTRO')==[]
    assert b.feed(b'LAB_PICO\r\n')==['HELLO,1,ASTROLAB_PICO']
    assert b.feed(b'x'*3000+b'\nRESET\n')==['RESET']

def test_commands():
    assert command_line('INPUT,P1,JUMP')=='INPUT,P1,JUMP\n'
    for line in ['INPUT,P3,RUN','RESET\nRESET','SET_MISSION,SATURN_JUMP,6,40','SET_MISSION,MARS,2,30']:
        with pytest.raises(ValueError): command_line(line)

def test_rejection_is_not_acceptance():
    assert parse_line('MISSION_REJECTED,SATURN_JUMP,NOT_READY')['type']=='mission_rejected'
