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

During missions, the animated tutorial shows only the required one or two movements:

- **Jump:** P1 Space / P2 I. **Duck:** P1 hold C / P2 hold K.
- **Steer:** P1 A/D. **Shake:** P1 Q / P2 U.
- Optional synchronized boost: **Q + U within one second**, giving both players a short shield/speed boost and 20 team points. Five-second recharge.
- The mouse/touch action buttons provide the same controls.
- All players share **one team score and one integrity meter**. There is no individual winner.

## The game flow

Launch (5 seconds) → fly toward a nearby planet → select it in range with E → transfer (4 seconds minimum, waiting for mission response if needed) → animated tutorial → **20-second mission** → team score.

Holding W accelerates the ship through actual world coordinates; S brakes. Nearby markers and objects move past the cockpit, Earth recedes, and destination planets grow as you approach. Releasing thrust slows the ship. Planet selection requires flying within 165 demo-distance units and traveling at least 20 units. Real solar-system distances are deliberately compressed.

Four implemented game types are available: **asteroid dodge** (steer + shake), **orbital slalom** (steer only), **meteor break** (shake only), and **ring relay** (jump + duck, Saturn). A per-planet history excludes the last two game types where alternatives exist, including when using local fallbacks. Names, settings and planet-specific story also vary. History survives restarting a round, but resets when the server restarts. Ring relay has two first-person views; other missions share a cockpit. Gas giants are explored from orbit.

## Live Gemini testing

In `backend/.env` set:

```dotenv
SIMULATE_PICO=true
VISION_ENABLED=false
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Restart the backend after changing `.env`. Select a planet in the cockpit. The backend uses the official `google-genai` SDK and a strict response schema. Gemini returns a game name, briefing, control instructions, implemented game type, obstacle count, and time limit. The generated type selects the corresponding scene and mechanics. Names, narrative, obstacle count, and time can vary; the engine does not execute arbitrary AI-generated code.

The briefing clearly displays **GEMINI** when a response is valid. A configured model returning 404/410 is retried with `gemini-flash-latest`; a successful alias is remembered for this server session. Your `.env` is never rewritten. Missing keys and failed/invalid calls display **LOCAL MISSION** with the reason category. Local fallback works offline. Live API verification results are reported in the chat; a configured key does not itself prove a successful call. Keys stay in the backend and `.env` is ignored by Git. Never paste a key into chat or frontend code.

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

The tests include player roles, stale-input neutralization, planet lock and generation, mission scene selection, collisions, cooperative hits, team completion bonuses and restart. The production build has a bundle-size advisory due to Three.js; the local demo runs via Vite's dev proxy.


## Updated demo controls and missions

Flight: P1 uses W/S to move vertically, holds F for forward thrust, and presses E/Enter to select a nearby planet. P2 uses left/right arrows to turn and J/L to tilt and level the ship. Releasing F slows the ship. These stand in for the two joysticks, buttons, and remote tilt input.

All eight planets can be visited at compressed demo distances. Keep exploring resumes flight from the current planet. Click the labelled ISS, Hubble, Webb, or comet models for NASA-linked facts; positions are illustrative, not live orbit telemetry.

Each mission lasts at most **20 seconds** and uses one or two movements for **both players**, with separate views and one team score. Missions include asteroid dodge (steer/shake), slalom (steer), meteor break (shake), beacon relay (steer/button), and obstacle courses (jump/duck). Saturn also offers ring races. Optional synchronized Q/U shaking gives a team boost.

Mission keys: P1 A/D and P2 left/right for steering; P1 Q and P2 U for shake; P1 E and P2 O for joystick-button clicks; P1 Space/C and P2 I/K for jump/duck. Jump/duck missions are included to showcase future OpenCV inputs, not required in every game. Animated tutorials show only the selected game's moves. There is no login or persistent score storage yet.
