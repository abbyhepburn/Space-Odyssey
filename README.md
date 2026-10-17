# Space Odyssey — 2-player planet party

A first-person planet exploration game with **two-player competitive 15-second mini-games**, a cinematic cockpit launch, real-object discoveries, and short, curated NASA-backed planet facts. Players jointly pilot a ship to a destination, then **compete for individual points** in the planet's mini-game.

The current playable version runs in **computer demonstration mode**: physical joysticks/ESP32 remotes and Mac webcam detection can be connected later via the game's normalized input command layer. No FPGA is needed for the game graphics: your Mac renders the React/Three.js interface to a monitor.

## Run on a Mac — two terminals

Requirements: Python 3.12 (recommended), Node.js and npm. From the project root:

**Terminal 1 — Python game backend**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If your Mac only has `python3` and it's a compatible version, use `python3 -m venv .venv`. Do not recreate a working environment unnecessarily. Store `GEMINI_API_KEY` in `backend/.env` (not in frontend or Git), and keep `SIMULATE_PICO=true` while using keyboard demo mode. **Never replace an existing `.env`.**

**Terminal 2 — React game frontend**

```bash
cd frontend
npm install
npm run dev
```

Open the printed Vite address (usually `http://127.0.0.1:5173`). Its proxy forwards backend traffic to port `8000`. Keep both terminals running. The FastAPI developer documentation, when enabled, is at `http://127.0.0.1:8000/docs`.

### Using an external monitor and laptop camera

Connect the Mac to the monitor by HDMI/USB-C. Go to **System Settings → Displays → Extend Display**. Move the game browser to the external monitor and use fullscreen. Keep the camera/debug window on the laptop screen. If you later enable the optional `VisionWorker`, install dependencies from `backend/requirements-vision.txt`, provide a MediaPipe `pose_landmarker_lite.task` model with the `POSE_MODEL_PATH` environment variable, and set `VISION_ENABLED=true`, `VISION_DEBUG=true`. **Camera + two-person calibration have not been verified against your webcam**; keyboard controls remain the fallback.

## Game sequence

1. Start with an animated cockpit menu. Click **Initiate Launch**, watch the ~13-second skippable boot sequence, then take control from Earth.
2. Player 1 handles forward/reverse thrust and turning; Player 2 keeps the ship level. Fly toward a planet and select it when in range.
3. The Gemini-generated *or validated local fallback* mission briefing explains a specific game type, short controls, and a curated NASA planet fact.
4. Each player plays in a split-screen 3D view. **Every mission lasts 15 seconds**; events are evenly distributed from approximately second 1 through 14.3 to avoid dead time.
5. The player with the higher **individual** score wins. Ties are possible. Select **New Game Here** or keep exploring.

Ground missions run only on rocky worlds — Mercury, Venus, Earth and Mars — and show terrain, a horizon, rocks and planet-specific lighting. Gas giants always use orbital courses or space challenges, not a fictional solid surface. All planet scales/orbits are illustrative, not simulated accurately.

## Controls in keyboard demo mode

| Action | P1 keyboard test | P2 keyboard test | Eventual physical control |
|---|---|---|---|
| Fly forward / reverse | Hold F / S | — | P1 joystick forward / backward |
| Turn spacecraft | A / D | — | P1 joystick left / right |
| Keep spacecraft level | — | J / L or left / right arrows | P2 remote tilt left / right |
| Select planet or start | E / Enter | — | P1 joystick button |
| Mission left/right steer or tilt | A / D | Left/right arrows | Each remote's tilt/joystick |
| Jump | Space | I | OpenCV pose detection |
| Duck | Hold C | Hold K | OpenCV pose detection |
| Shake | Q | U | Remote accelerometer shake |
| Press joystick | E | O | Remote button |
| Flick upward | R | P | Remote accelerometer flick |

The production UI displays **physical movements only**, not these keyboard
shortcuts. Test keys work regardless; append `?debugControls=1` to the local
browser URL to show test buttons. See [REMOTE_AND_KEYBOARD_TESTING.md](REMOTE_AND_KEYBOARD_TESTING.md).

The game backend receives normalized strings such as `FLIGHT,P1,JUMP`, `FLIGHT,P2,DUCK_ON`, `FLIGHT,P1,SHAKE`, `FLIGHT,P2,UPWARD_FLICK` and `FLIGHT,P1,AXIS,1,0`. Hardware input bridging is a **future integration**. Do not claim it works with the physical remotes yet.

## Different mini-games

- **Surface Run:** jump hurdles and duck under barriers on a real-looking planetary terrain.
- **Crater Leap:** jump pits and flick the remote upward to cross ridges.
- **Sample Hunt:** tilt toward glowing minerals and press to collect them before your opponent.
- **Storm Shelter:** duck incoming storm fronts and shake to activate outpost generators.
- **Asteroid Dodge:** steer away or shake to destroy asteroids in your own lane.
- **Meteor Break:** time your shake to break incoming meteorites.
- **Orbital Slalom:** dodge rocks by steering; no extra/unrelated sync action.
- **Beacon Relay:** steer toward signals and press to collect beacons.
- **Ring Race:** jump/duck around an illustrative orbital course near Saturn's rings.

Each implemented game type has its own **fixed and tested mechanics**. Gemini can vary the narrative and title, but cannot invent hardware inputs or live arbitrary game code. Modes avoid repeating the previous two on the same planet when alternatives exist.

### Meaningful optional sync

Several challenges award **+8 points to each player** when the players match a relevant action within 0.8 seconds. For example, synchronize **JUMP** in Surface Run, **FLICK** in Crater Leap, **PRESS** in Sample Hunt/Beacon Relay, or **SHAKE** in storm/asteroid games. It also gives a brief defensive advantage to both players; individual rankings remain competitive. Orbital Slalom has no sync action because an unrelated shake would not fit that game's mechanic. Sync is *not required* to play or win.

## Space encyclopedia

In flight, click the models/labels or open **Discoveries** to browse **15 real space objects** including ISS, Hubble, Webb, GOES-16, Landsat 9, GPS III, Halley's Comet, the Sun, Earth's Moon, Europa, Io, Titan, Orion Nebula, Crab Nebula, and Andromeda Galaxy. Each information panel contains categorized facts, educational details, and a link to NASA, NOAA or another science agency. **Positions are illustrative** — distant stars, galaxies and nebulae are not physically orbiting the planets.

## Tests

```bash
cd backend
python -m pytest -q
cd ../frontend
npm run build
```

The backend suite passed **78 tests** in this review environment; **10 JavaScript tests** also passed. JSX source also passed a TypeScript syntax parsing check. **The frontend production build and browser/hardware/camera tests could not be completed in the development environment because npm dependency installation was unavailable**; run `npm install && npm run build` on your Mac. If any errors occur, share the console/terminal output. We did not test a live Gemini API key.

### Important implementation files

- `backend/flight_game.py` — planet selection, motion event handling, game type rules, timed events, individual scores, winner and curated education.
- `frontend/src/App.jsx` — display state, actions, scoreboard, briefings, discoverable facts and controls.
- `frontend/src/components/SurfaceLandscape.jsx` — rocky planet ground scenes.
- `frontend/src/components/CockpitGame.jsx` — cockpit, missions, 3D satellites and star objects.
- `frontend/src/components/SpaceOdysseyLaunch.jsx` + `.css` — cinematic opening and skippable startup.
- `backend/vision.py` — optional MediaPipe two-player pose worker with debug preview (requires configuration/testing).

Local scores currently reset when the game restarts. Persistent per-player leaderboards/login are not part of this update.

## Educational game variety update

See [GEMINI_VARIETY_UPDATE.md](GEMINI_VARIETY_UPDATE.md) for the current 11 mission families, new gravity-gate and relay-repair games, three game-layout rules, cross-planet anti-repeat selection, rotating NASA-linked facts, keyboard stand-ins, and verification details.


## Forward-thrust test before merging

Use the **real React/Three.js game** to review thrust, steering and reverse. Hold F to move forward, S to reverse, and A/D to steer. The HUD gauge uses the backend-reported throttle. Remote input messages share the same flight authority; the physical firmware still needs implementation and integration testing.
