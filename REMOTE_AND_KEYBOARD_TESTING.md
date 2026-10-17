# Dual input control — deployment vs testing

The visible **game screen teaches real controls only**. The computer keyboard is
still fully supported by the Python game authority for development and demos.
Add `?debugControls=1` to the frontend URL for onscreen keyboard test buttons.
The keyboard works even when those buttons are hidden.

## Navigation mapping

| Action | Player 1 remote | Test key |
|---|---|---|
| Forward | P1 joystick forward | Hold F |
| Reverse | P1 joystick backward | Hold S |
| Turn left/right | P1 joystick left/right | Hold A/D |
| Select planet/start game | P1 joystick button | E or Enter |
| Stabilize roll | P2 remote tilt left/right | J/L or arrow keys |

During missions both players use their own joystick or gestures (tilt, shake,
upward flick, button press) and their own jump/duck webcam input. See README
for computer mission mappings. A mission-specific sync bonus is optional.

## Unified backend transport

All inputs reach the same Python `FlightGame` authority:
- Browser keyboard/test UI: `FLIGHT,P1,AXIS,<forward>,<steer>` and other
  `FLIGHT,P1,...` / `FLIGHT,P2,...` action commands.
- Future Pico USB lines: `REMOTE,P1,AXIS,<forward>,<steer>`,
  `REMOTE,P2,AXIS,0,<roll_correction>`, and
  `REMOTE,P1,SELECT` / `REMOTE,P2,SHAKE` / etc. The backend's
  `control_inputs.py` validates these and converts them to the same FLIGHT actions.
- OpenCV (optional): normalized JUMP, DUCK_ON, DUCK_OFF events.

**Important:** The remote firmware has not been implemented or validated yet.
The `REMOTE,...` format is a proposed input contract for connecting the Pico
later; do not assume the current firmware already emits those lines.

If both a remote and computer test keys are active, the backend prioritizes fresh
remote analog readings. If the remote goes silent for 400 ms, axes return to
keyboard test control; if neither supplies current axes, they go to neutral.
This prevents the browser's continuously sent idle axes from canceling motion
from an actual joystick. No physical calibration has been performed.

### Test without hardware

With the game backend running on 127.0.0.1:8000 in simulator mode, use
Python `requests`, curl, or the FastAPI /docs to POST:

```
POST /api/control
{"command":"FLIGHT,P1,AXIS,1,0"}
```

To emulate remote joystick axes, send `{"command":"REMOTE,P1,AXIS,0.5,-0.25"}`.
To emulate the joystick button, send `{"command":"REMOTE,P1,SELECT"}`.
Both control paths are local-only and share the same backend behavior.
