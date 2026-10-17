# Space Odyssey: Two-player iPhone camera + MediaPipe (Mac)

This is a **drop-in addition**, not a replacement for your game. It does not replace
`frontend/`, `flight_game.py`, your planets/Saturn rings, or `backend/.env`.

## What these files do

| File | Purpose |
|---|---|
| `backend/camera_vision.py` | Runs the iPhone/webcam, MediaPipe two-person landmarks, P1/P2 preview, sends events. |
| `backend/pose_movements.py` | Calibrates shoulders/hips, detects **JUMP**, **DUCK_ON**, **DUCK_OFF**; no external packages needed for its tests. |
| `backend/vision_route.py` | Adds local-only HTTP endpoints to your existing FastAPI backend, forwarding actions through the **existing `Engine.consume()`** input queue. |
| `backend/download_pose_model.py` | One-time download of official MediaPipe Pose Landmarker Lite model. |
| `backend/requirements-vision-mediapipe.txt` | MediaPipe and OpenCV dependencies, plus your existing backend dependencies. |
| `backend/tests/test_pose_movements.py`, `test_vision_route.py` | Automated tests. |
| `apply_camera_patch.py` | Makes a small, idempotent edit to **your current** `backend/main.py` with a backup; no other files overwritten. |

**No frontend edits are required.** During game challenges the event flow is:

```
iPhone (or Mac built-in camera)  -> OpenCV + MediaPipe Pose (on MacBook)
   -> P1_JUMP / P1_DUCK_ON / P1_DUCK_OFF  (and the P2 equivalents)
   -> HTTP POST http://127.0.0.1:8000/api/vision/event
   -> FastAPI Engine.submit('input', 'INPUT,P1,JUMP')
   -> existing FlightGame/Exploration authority
   -> React Game WebSocket updates on the external monitor
```

Camera frames **never go to Gemini or the browser**. Video isn't uploaded or stored.

## A. Install into your existing VS Code project (do once)

**1. Back up your original project in Finder.** Download the camera ZIP and place it in Downloads.

Run in VS Code Terminal:

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey"
unzip -n "$HOME/Downloads/Space_Odyssey_MediaPipe_iPhone_Integration.zip" -d .
python3 apply_camera_patch.py
```

`apply_camera_patch.py` creates `backend/main.py.before-camera.bak` before editing.
If you've already run it, a second run won't add duplicate routes.

**2. Open `backend/.env`** and ensure you have this setting (only **one** copy):

```dotenv
VISION_ENABLED=false
SIMULATE_PICO=true
```

`VISION_ENABLED=false` is intentional: the **separate** `camera_vision.py` process owns the camera and draws the preview. If it's true, the old embedded `vision.py` may open the camera a second time.

Keep `GEMINI_API_KEY` as it is; never paste it into chats or GitHub.

**3. Use the backend's existing virtual environment** (Python 3.12 recommended on Mac):

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/backend"
source .venv/bin/activate
python --version
python -m pip install -r requirements-vision-mediapipe.txt
python download_pose_model.py
```

If `.venv` doesn't exist, create it with:

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
```

The MediaPipe model is stored locally at `backend/models/pose_landmarker_lite.task` and should be ignored by Git.

## B. Set up the iPhone as a camera

Apple's **Continuity Camera** can use your iPhone as a Mac camera, wirelessly or via USB:

1. On iPhone: **Settings → General → AirPlay & Continuity → Continuity Camera = On**.
2. iPhone and Mac: use the **same Apple Account** with two-factor authentication, Wi-Fi and Bluetooth enabled, and keep them nearby.
3. Mount the iPhone **landscape**, rear camera facing the players; keep it steady and preferably plugged in by USB. Lock the iPhone after setting it up.
4. Test in **FaceTime / Photo Booth**: choose the iPhone as the video camera in that app's camera menu.
5. In macOS **System Settings → Privacy & Security → Camera**, permit camera access to the terminal/VS Code/Python app if prompted.
6. Quit the app using the camera if it prevents OpenCV from opening the same feed.

Sources: [Apple Continuity Camera](https://support.apple.com/en-lamr/102546) and [MediaPipe Pose Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python).

**Important:** The iPhone can work in FaceTime yet NOT appear in `cv2.VideoCapture`. Apple's AVFoundation/Continuity Camera selection and OpenCV camera indices are not guaranteed to match. If that happens, test the Mac built-in webcam first, try USB, restart the terminal, or use an iPhone webcam app exposing a virtual camera accessible to OpenCV. There is no need to create an iPhone app for the first version.

List cameras (the scan may take a few seconds):

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/backend"
source .venv/bin/activate
python camera_vision.py --scan
```

Try `--camera 0`, `--camera 1`, or `--camera 2` based on the scan result. **The index is not guaranteed to correspond to the iPhone.**

## C. Test camera-only first (no game needed)

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/backend"
source .venv/bin/activate
python camera_vision.py --camera 0 --no-send
```

A local window will display a **full frame** with a vertical center divider. The two players are **not cropped into two separate feeds**: MediaPipe sees both bodies together, then the script labels P1 on the left and P2 on the right. This retains context and reduces identity swaps.

- Both stand upright with knees mostly straight until **P1 READY / P2 READY**.
- Jump physically: console prints `LOCAL TEST: P1 JUMP` (or P2).
- Duck physically: prints `DUCK_ON`, then `DUCK_OFF` when standing up.
- Press `C` while the camera preview is focused to recalibrate; press `Q` or `Esc` to quit.
- Stay in your respective halves. The center dead zone avoids uncertain identity. If you cross, return to your half and press `C`.

By default the preview is mirrored to feel like a mirror. Use `--no-mirror` if the player sides are reversed relative to where you want them.

If movements are too sensitive or not sensitive enough:

```bash
python camera_vision.py --camera 0 --no-send --jump-ratio 0.18 --duck-ratio 0.22
```

Lower thresholds make events easier to trigger. The algorithm uses shoulders **and hips** to reduce false jumps from arm waving, and knee angle + persistence to confirm ducks.

## D. Run the GAME and camera on two screens

Use **System Settings → Displays**, set your external monitor to **Extend** (not Mirror), and drag the browser window to the external monitor. Fullscreen that browser window. Keep camera and terminal windows on the MacBook screen.

**Terminal 1 — Python backend (on laptop):**

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/backend"
source .venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — React (game on monitor):**

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/frontend"
npm run dev
```

Open `http://127.0.0.1:5173/` in a browser, move that browser to the monitor, and fullscreen it.

**Terminal 3 — live MediaPipe tracking (on MacBook):**

```bash
cd "$HOME/Documents/GitHub/Space-Odyssey/backend"
source .venv/bin/activate
python camera_vision.py --camera 0
```

The camera window stays on your MacBook; your game stays on the external monitor.

To confirm the camera route is online, watch for `BACKEND CONNECTED` in the camera preview. If it says `BACKEND OFFLINE`, verify the backend is running at `127.0.0.1:8000` and the router was installed.

In a *fourth* terminal, you can send one test action without a camera:

```bash
curl -X POST http://127.0.0.1:8000/api/vision/event \
  -H 'Content-Type: application/json' \
  -d '{"player":"P1","action":"JUMP"}'
```

This should return `{"ok":true}`. The action is visibly relevant only if a mission that uses JUMP is active.

## E. Hardware integration later

**No changes to your remotes or Pico firmware** are included. Continue using keyboard and remote test controls as before. When you finish the BLE joystick integration, keep the camera on the same Mac and keep the **remote motion events independent**. Both converge in the current Python game rules.

In hardware mode, make sure `SIMULATE_PICO=false` and a proper Pico serial port is configured. The camera routes already accept P1/P2 jump and duck, and its heartbeat enables vision capabilities. If the camera stops reporting for more than 3.5 seconds, the backend lowers the vision readiness flags and releases held ducks. The physical USB/BLE path must be tested on the actual devices.

## F. Troubleshooting

| Symptom | Action |
|---|---|
| `python: command not found` | Run `source .venv/bin/activate` from `backend/` first. |
| Python 3.15 / `No module named mediapipe` | Use Python 3.12 virtual environment; install `requirements-vision-mediapipe.txt` with activated `python -m pip`. |
| `Pose model not found` | Run `python download_pose_model.py` once while online. |
| iPhone isn't camera 0 | Run `python camera_vision.py --scan`; try another index or built-in camera. |
| macOS camera denied | System Settings → Privacy & Security → Camera, enable the app launching Python; relaunch Terminal/VS Code. |
| Only P1 gets detected | Ensure both bodies are fully visible head-to-feet, in separate halves; move iPhone farther back and recalibrate. |
| Jump mistakenly detected on head bob | Check iPhone mount stability, adjust `--jump-ratio` upward (e.g. 0.27). |
| Duck triggered while jumping | Adjust `--duck-ratio` upward and require upright calibration. |
| Events print, but game doesn't react | Test `curl` endpoint, check backend running, start a **JUMP/DUCK-enabled mission**, and inspect `/state` or the mission UI. |
| `VISION_ENABLED=true` in `.env` | Set to `false` when running **separate** `camera_vision.py`. |
| Camera is slow | Try `--width 640 --height 360` and disable iPhone camera effects. |

## Git ignore additions

Add these to the **existing** root `.gitignore` (don't replace it):

```gitignore
backend/models/
backend/main.py.before-camera.bak
backend/__pycache__/
```

Commit the new Python source, requirements file, and the patch to `main.py`. Do **not** commit `backend/.env`, the model `.task` file, or video recordings.

## What is verified

- The new pure-Python tracker, camera route, and **all 93 backend tests** passed when the patch was applied to the latest review copy available here.
- `compileall` passed for the Python files.
- Actual MediaPipe inference, live iPhone camera selection, USB hardware, and visual two-screen behavior **cannot be verified in this sandbox**; test these on your Mac.
