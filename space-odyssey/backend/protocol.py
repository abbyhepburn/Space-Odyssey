"""Strict wire protocol. Invalid/log frames return None; never become game state."""
import re
from dataclasses import dataclass, asdict

IDS = {'SATURN_SPRINT', 'SATURN_JUMP', 'SATURN_DUCK'}
PLAYERS = {'P1', 'P2'}
ACTIONS = {'RUN', 'JUMP', 'DUCK_ON', 'DUCK_OFF'}

@dataclass
class State:
    phase: str = 'CUTSCENE'
    planet: str = 'TRANSIT'
    p1_distance: int = 0
    p2_distance: int = 0
    p1_pose: str = 'NORMAL'
    p2_pose: str = 'NORMAL'
    score1: int = 0
    score2: int = 0
    mission_id: str = 'NONE'
    progress1: int = 0
    progress2: int = 0
    winner: str = 'NONE'
    elapsed_ms: int = 0

    def line(self):
        return 'STATE,' + ','.join(map(str, asdict(self).values()))


def natural(s):
    if not re.fullmatch(r'[0-9]{1,10}', s):
        raise ValueError('Expected unsigned integer')
    return int(s)


def parse_line(line):
    if len(line) > 1024:
        return None
    p = line.strip('\r\n').split(',')
    try:
        kind = p[0]
        if kind == 'STATE' and len(p) == 14:
            if p[1] not in {'CUTSCENE','COUNTDOWN','RACE','RESULTS'} or p[2] not in {'TRANSIT','SATURN'}:
                return None
            if any(x not in {'NORMAL','JUMP','DUCK'} for x in p[5:7]): return None
            if p[9] not in IDS | {'NONE'} or p[12] not in PLAYERS | {'NONE','TIE'}: return None
            for i in (3,4,7,8,10,11,13): p[i] = natural(p[i])
            return {'type':'state', 'state':asdict(State(*p[1:]))}
        if kind == 'HELLO' and p == ['HELLO','1','ASTROLAB_PICO']:
            return {'type':'hello','version':1}
        if kind == 'MISSION_ACCEPTED' and len(p) == 2 and p[1] in IDS:
            return {'type':'mission_accepted','mission_id':p[1]}
        if kind == 'MISSION_REJECTED' and len(p) == 3 and p[1] in IDS and p[2]:
            return {'type':'mission_rejected','mission_id':p[1],'reason':p[2]}
        if kind == 'MISSION_COMPLETED' and len(p) == 3 and p[1] in IDS and p[2] in PLAYERS:
            return {'type':'mission_completed','mission_id':p[1],'player':p[2]}
        if kind == 'EVENT' and len(p) == 4 and p[1] and p[2] in PLAYERS | {'NONE','TIE'}:
            return {'type':'event','kind':p[1],'player':p[2],'value':p[3]}
    except (ValueError, TypeError):
        pass
    return None


def command_line(command):
    """Validate all outgoing commands and terminate exactly once."""
    p = command.split(',')
    valid = command in {'RESET','SKIP_CUTSCENE','GET_STATE'}
    valid |= len(p)==3 and p[0]=='INPUT' and p[1] in PLAYERS and p[2] in ACTIONS
    valid |= len(p)==3 and p[0]=='CAPABILITIES' and all(v in {'0','1'} for v in p[1:])
    if len(p)==4 and p[0]=='SET_MISSION' and p[1] in IDS:
        from mission_catalog import BOUNDS
        lo,hi,tlo,thi = BOUNDS[p[1]]
        valid |= lo <= natural(p[2]) <= hi and tlo <= natural(p[3]) <= thi
    if not valid: raise ValueError('Invalid command')
    return command + '\n'


class LineBuffer:
    """Partial reads persist; oversized frames are discarded until newline."""
    def __init__(self): self.data = bytearray(); self.dropping = False
    def feed(self, chunk):
        lines = []
        for b in chunk:
            if b == 10:
                if not self.dropping:
                    lines.append(self.data.decode('utf-8', errors='replace').rstrip('\r'))
                self.data.clear(); self.dropping = False
            elif not self.dropping:
                self.data.append(b)
                if len(self.data)>1024: self.data.clear(); self.dropping=True
        return lines
