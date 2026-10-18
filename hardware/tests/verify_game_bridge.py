"""Run after building controller_protocol.cpp; uses the actual deployed parser/game."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()/'backend'))
from control_inputs import remote_to_flight
from flight_game import FlightGame
lines=subprocess.check_output([sys.argv[2]],text=True).splitlines()
g=FlightGame();g.transition('NAVIGATION');g.ship=[0.,100.,100.]
g.command(remote_to_flight(lines[0]),source='remote')
assert g.active_axes()[0]==[1.,-.5]
y=g.ship[1];z=g.ship[2];g.tick(.1)
assert g.ship[2]<z and g.ship[1]==y
# Keyboard-neutral packets must not overwrite a live physical controller.
g.command('FLIGHT,P1,AXIS,0,0');assert g.active_axes()[0]==[1.,-.5]
g.command(remote_to_flight(lines[1]),source='remote');assert g.active_axes()[0]==[0.,0.]
g.command(remote_to_flight(lines[2]),source='remote');assert not g.controller_snapshot()[0]['fresh']
print('PASS: BLE snapshots -> USB lines -> real game parser, movement, center and disconnect')
