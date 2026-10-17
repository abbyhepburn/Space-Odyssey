"""Normalize physical remote events to the existing FlightGame command language.

Physical Pico firmware will eventually emit one newline-delimited REMOTE event:
    REMOTE,P1,AXIS,<forward-backward>,<left-right-steering>
    REMOTE,P2,AXIS,0,<roll-correction>
    REMOTE,P1,SELECT (joystick click)
    REMOTE,P1,SHAKE / UPWARD_FLICK / PRESS

Camera JUMP / DUCK_ON / DUCK_OFF and keyboard FLIGHT commands remain
separate producers of the same validated FlightGame actions.
"""
import math

PLAYERS={'P1','P2'}
EVENTS={'SELECT','PRESS','SHAKE','UPWARD_FLICK','JUMP','DUCK_ON','DUCK_OFF'}


def remote_to_flight(line):
    """Return a validated FLIGHT command, or raise ValueError.

    This intentionally does not accept arbitrary FLIGHT strings or UI commands.
    """
    fields=line.strip().split(',')
    if len(fields)<3 or fields[0]!='REMOTE' or fields[1] not in PLAYERS:
        raise ValueError('Invalid remote event')
    if fields[2]=='AXIS' and len(fields)==5:
        try:
            x,y=(float(s) for s in fields[3:])
        except ValueError as exc:
            raise ValueError('Invalid remote axes') from exc
        if not all(math.isfinite(v) and -1.0<=v<=1.0 for v in (x,y)):
            raise ValueError('Remote axes must be finite and normalized')
        return f'FLIGHT,{fields[1]},AXIS,{x},{y}'
    if len(fields)==3 and fields[2] in EVENTS:
        return f'FLIGHT,{fields[1]},{fields[2]}'
    raise ValueError('Unsupported remote event')
