# Run the updated game

From this repository:

```sh
source backend/.venv/bin/activate
python -m pip install -r backend/requirements-vision.txt
cd frontend
npm ci
npm run build
cd ..
python start_game.py --serial /dev/cu.usbmodemYOUR_PICO
```

Use `python -m serial.tools.list_ports` to find the Pico port. To test without hardware, set SIMULATE_PICO=true in backend/.env and omit --serial. Close any old backend on port 8000 first, or add --port 8002. The launcher opens the camera separately and serves the built game. Move the game browser to the HDMI monitor; leave the OpenCV window on the laptop. macOS may ask for camera access. Keep both players' shoulders visible, P1 on the left of the mirrored preview, P2 on the right. Tracking starts immediately from visible shoulders. C resets tracking; Q exits the camera. The **Open laptop camera** button can reopen it. See backend/camera-preview.log if it fails.

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

Python owns gameplay; the Pico bridges physical controls. The UI's two cursors show raw joystick readings. Expand diagnostics for packet age/count, last action and effective game axes. USB connected does not imply remote packets are arriving. Input older than 400 ms stops safely. P1 joystick controls thrust/steering in navigation; P2 tilt controls roll. Challenge controls are shown before every round.

If an axis is backwards, set the relevant sign to -1 in backend/.env and restart (no reflash): P1_FORWARD_SIGN, P1_STEER_SIGN, P1_TILT_SIGN, P2_FORWARD_SIGN, P2_STEER_SIGN, P2_TILT_SIGN. Defaults are 1. Camera source index can be set with CAMERA_INDEX=0 or another index.

Quizzes are excluded from generation. Gemini chooses supported action mechanics, names, briefings and encounter patterns; Python validates movement rules, 15-second rounds and scoring. Ground/ring body courses have a three-second ready countdown and four spaced hazards with advance cues. Ground/ring/orbital shortcut buttons are available in each planet briefing.

For hosting and domain setup, read DEPLOY.md.
