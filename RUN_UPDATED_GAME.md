# Run the updated game

From this repository:

```sh
source backend/.venv/bin/activate
cd frontend
npm ci
npm run build
cd ..
python start_game.py --serial /dev/cu.usbmodemYOUR_PICO
```

Use `python -m serial.tools.list_ports` to find the Pico port. To test without hardware, set SIMULATE_PICO=true in backend/.env and omit `--serial`. Close any old backend on port 8000 first, or add `--port 8002`. The launcher serves the built game; move the game browser to the HDMI monitor. No camera is required.

## Controllers

Flash **both** ESP sketches and the Pico receiver from `hardware/`. Their GPIO assignments preserve the Hardware branch: joystick X=34, Y=35, button=25; I2C SDA=21/SCL=22. P1 uses MPU6050, P2 MPU9250. Keep sticks centered during startup calibration.

Use the Earle Philhower Arduino-Pico board package, select Raspberry Pi Pico 2 W and enable Bluetooth for the central sketch. ESP sketches use the ESP32 Arduino core and BLE libraries. No hardware was flashed automatically.

The remotes send periodic full stick/tilt state every ~80 ms. The Pico scans continuously and sends newline-delimited USB records at 115200 baud:

```
REMOTE,P1,STATE,0.50,-0.25,0.00
REMOTE,P2,SELECT
REMOTE,P1,SHAKE
REMOTE,P2,UPWARD_FLICK
```

Python owns gameplay; the Pico bridges physical controls. In flight, P1 joystick controls thrust/steering and P2 tilt controls roll. In missions, tilt each remote up to jump and push its joystick forward to duck; normal flight steering remains unchanged. The UI's two cursors show raw joystick readings. Expand diagnostics for packet age/count, last action and effective game axes. USB connected does not imply remote packets are arriving. Input older than 400 ms stops safely.

If an axis is backwards, set the relevant sign to -1 in backend/.env and restart (no reflash): P1_FORWARD_SIGN, P1_STEER_SIGN, P1_TILT_SIGN, P2_FORWARD_SIGN, P2_STEER_SIGN, P2_TILT_SIGN. Defaults are 1.

Quizzes are excluded from generation. Gemini chooses supported action mechanics, names, briefings and encounter patterns; Python validates movement rules, 15-second rounds and scoring. Ground/ring body courses have a three-second ready countdown and four spaced hazards with advance cues. Ground/ring/orbital shortcut buttons are available in each planet briefing.

For hosting and domain setup, read DEPLOY.md.

## Optional OpenCV camera experiment
To try local camera tracking, install `backend/requirements-vision.txt` in the Python 3.12 backend environment, confirm `backend/models/pose_landmarker_lite.task` exists, and run `python backend/camera_vision.py --scan` from Terminal. macOS must allow Terminal camera access. The camera tracker is optional and has not been verified with two players; remote tilt-up jump and joystick-forward duck remain the intended controls.

## Joystick flight
P1 joystick forward (W or F) moves forward; pull backward (S) to reverse. Altitude stays level. Left/right turns; P2 tilt stabilizes roll. The ship starts beside Earth at the same height. No firmware update needed.
