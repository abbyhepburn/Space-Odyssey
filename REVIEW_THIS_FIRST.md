# Space Odyssey — complete project review (October 17, 2026)

**This is one consolidated copy of the user's original Space Odyssey project plus all of the accumulated game updates.** The old diagnostic preview has been excluded because its simplified drawing did **not** represent the actual Three.js planets.

## Important: original planets untouched

The original React `Planet` component in `frontend/src/components/CockpitGame.jsx` is byte-for-byte identical to the component in the original `Space-Odyssey-main.zip`, including the 4 Saturn ring meshes and their materials. The `frontend/src/components/OrbitalScene.jsx` shader module is also byte-for-byte identical. New **planet surface mission backgrounds** are separate, not replacements for the original navigable space planets.

## Features included in this ZIP

- Actual original 3D solar-system exploration, including Saturn rings and planet shader.
- Cinematic, skippable cockpit-startup animation and controls tutorial.
- 15-second **Player 1 versus Player 2** minigames and individual results (not cooperative team scores).
- 11 approved minigame families, including crater leap, sample hunt, storm shelter, relay repair and gravity gate dash, and orbital/space challenges. Three rule variants and cross-planet anti-repetition.
- Actionable events spread across the **entire 15 seconds**.
- Planet-specific surface views for ground games; existing space views for asteroid/comet/orbit games.
- Curated planet science facts rotated between games; Gemini supplies safe mission storytelling but **does not invent unsupported mechanics or facts**.
- A Discoveries/Space Encyclopedia with 15 selectable objects including satellites, moons, star, nebulae and galaxy, with source links. Positions are illustrative, not physically scaled.
- Mission-context optional synchronized actions; P1/P2 results remain competitive.
- Thrust fix: **hold F** = joystick-forward surrogate; release F to brake. On-screen thrust is hold-to-activate. Throttle gauge is sourced from game state. Controller axis accepts a fractional [0,1] thrust input, but **physical remotes are not integrated yet**.
- Keyboard stand-ins for future remote shake, tilt, flick up, buttons and OpenCV jump/duck.

## Preview this exact FULL GAME, before replacing any local files

1. Unzip into a **new folder**, away from your existing `~/Documents/GitHub/Space-Odyssey`. Do not overwrite the original.
2. Open VS Code in the new folder.
3. In Terminal 1 (from this folder), run these commands one line at a time:

   ```bash
   cd backend
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   SIMULATE_PICO=true python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

   If `python3.12` is not installed, install it (`brew install python@3.12`) or use another **compatible** existing Python version. If another server owns port 8000, stop it first. Your existing Gemini `.env` has deliberately **not** been copied; offline/fallback mode can run without a key.
4. In Terminal 2 (from this folder):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Visit the Vite URL, usually `http://127.0.0.1:5173`. This is the **real React/Three.js game**, **not** the simplified thrust diagnostic. Observe the original Saturn rings, play the intro, and test **hold F** during navigation; release to brake. Select planets for the 15-second P1-vs-P2 games.
6. Keep your original GitHub checkout untouched until you approve this copy. To use Gemini again after approval, copy your own local `backend/.env` into the reviewed project privately; never share or commit it.

## Tests and limitations

- Backend: **78 tests passed** on this project copy.
- JS flight controls: **10 Node tests passed**.
- Exact planet component and original planet shader comparison: **PASS**.
- Earlier live FastAPI WebSocket thrust tests passed for full, half and released input.
- **Not verified**: full Vite build and browser end-to-end in this environment (dependencies could not be installed from npm here), physical remotes, webcam detection, monitor/dual-screen configuration, and live Gemini calls.
- OpenCV is provided as a separate/backend module but real camera tracking, calibration and integration still need hardware testing.
- Team score persistence without login was an earlier requested feature but **is not implemented or claimed in this ZIP**. Round scores are individual per-player.

## Sources

See `UPDATE_NOTES.md`, `GEMINI_VARIETY_UPDATE.md` and the source code for more detail.

## Updated input behavior

- On-screen deployment instructions describe actual remotes and camera movements.
- Keyboard control remains active for testing, with optional `?debugControls=1` buttons.
- P1 remote joystick / keyboard F,S,A,D operates forward, reverse and turning.
- P2 remote tilt / keyboard J,L controls roll only, never heading.
- Backend `control_inputs.py` normalizes future Pico `REMOTE,...` messages;
  remote analog input takes priority over keyboard test axes until 400 ms stale.
- Physical remotes have **not** been connected or tested. Full input contract:
  [REMOTE_AND_KEYBOARD_TESTING.md](REMOTE_AND_KEYBOARD_TESTING.md).
