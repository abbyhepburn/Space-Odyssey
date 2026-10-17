# Space Odyssey — two-player cockpit demo

The current app is a first-person spacecraft game preview. It launches from Earth, shows nearby planets through the cockpit windows, and loads a named mission with movement instructions after a planet is selected. The route is deliberately compressed for a 2–3 minute demonstration.

**No hardware, Pico firmware, webcam, or OpenCV setup is required.** Python owns local game state for this prototype. The React/Three.js client is a fullscreen game renderer. ESP/Pico integration is future work; no invented flight commands are sent to existing firmware.

## Run on Windows in two VS Code terminals

Use Python 3.12 and Node.js 22 or later.

Terminal 1:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --host 127.0.0.1
```

Do not overwrite an existing configured `.env`. If activation is blocked, invoke `.\.venv\Scripts\python.exe -m pip` and `.\.venv\Scripts\python.exe -m uvicorn` directly.

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally http://127.0.0.1:5173/. Click the fullscreen icon or press F11. For an external monitor, use Windows+P → Extend and move the browser onto that monitor.

## Computer controls

During flight:

- Player 1: **W/S** increase/decrease forward thrust; **A/D** turn; **E or Enter** selects the planet centered in the reticle. Enter also launches and starts a briefed mission.
- Player 2: **left/right arrows** counter the ship's roll and keep the artificial horizon level.
- The cockpit's held buttons provide mouse/touch alternatives. Click inside the game before using keys.
- **H** opens the control guide; the restart icon returns to Earth.

During missions:

- P1: A/D steering, **Space** jump, **C** hold to duck, **Q** shake, **R** upward flick/boost.
- P2: arrows steer during a race (stabilize during spacecraft missions), **I** jump, **K** hold to duck, **U** shake, **O** upward flick/boost.
- Shake together with **Q + U within one second** to hit a large asteroid in range.
- Visible action buttons also work. Duck buttons must be held.

## The game flow

Launch (5 seconds) → navigate nearby planets → select via joystick-button substitute (E) → transfer (4 seconds minimum, waiting for mission response if needed) → briefing → mission (45–60 second limit) → scores and restart.

Saturn supports a constructed ring-track race with jump hurdles, duck gates, and rocks. Mars, Jupiter and Neptune support cooperative orbital asteroid dodging. Gemini can also choose asteroid dodging at Saturn. The race switches to two first-person views. Other phases share one cockpit: one pilot, one flight engineer. These are game environments, not an astrophysically accurate flight model. Gas giants are visited in orbit.

## Live Gemini testing

In `backend/.env` set:

```dotenv
SIMULATE_PICO=true
VISION_ENABLED=false
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Restart the backend after changing `.env`. Select a planet in the cockpit. The backend uses the official `google-genai` SDK and a strict response schema. Gemini returns a game name, briefing, control instructions, implemented game type, obstacle count, and time limit. The generated type selects the corresponding scene and mechanics. Names, narrative, obstacle count, and time can vary; the engine does not execute arbitrary AI-generated code.

The briefing clearly displays **GEMINI** when a response is valid. Missing keys and failed/invalid calls display **LOCAL MISSION** with the reason category. Local fallback works offline. An actual Gemini call has not been verified without an API key. Keys stay in the backend and `.env` is ignored by Git. Never paste a key into chat or frontend code.

## Implementation

- `backend/flight_game.py`: draft input contract, launch/navigation/stabilization, generation, obstacle physics, collision checks, scores.
- `frontend/src/components/CockpitGame.jsx`: procedural spacecraft interior, instruments, gloves, stars, shaded planets and first-person game scenes.
- `frontend/src/App.jsx`: computer controls and in-game HUD/briefing.
- `backend/main.py`: HTTP/WebSocket transport; `/state` includes `flight`.

Draft **local-only** commands: `FLIGHT,LAUNCH`, `FLIGHT,RESET`, `FLIGHT,P1,AXIS,0.5,1`, `FLIGHT,P2,AXIS,-0.3,0`, `FLIGHT,P1,SELECT`, `FLIGHT,P1,JUMP`, `FLIGHT,P2,DUCK_ON`, `FLIGHT,P2,DUCK_OFF`, `FLIGHT,P1,SHAKE`, `FLIGHT,P2,UPWARD_FLICK`. Axes are normalized −1…1 and neutralize after 400 ms without fresh input.

The older Saturn-only protocol/serial, camera, and planet-menu modules remain in the repository for reference. They are not the current entry screen, and the finalized hardware contract still needs agreeing. Camera support is optional and not needed to test this demo.

## Verify

```powershell
cd backend
python -m pytest -q
cd ..\frontend
npm run build
```

The tests include player roles, stale-input neutralization, planet lock and generation, mission scene selection, collisions, cooperative hits, winner bonuses and restart. The production build has a bundle-size advisory due to Three.js; the local demo runs via Vite's dev proxy.
