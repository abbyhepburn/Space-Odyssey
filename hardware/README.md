# Matching ESP32 → Pico 2 W → laptop firmware

Flash **all three** sketches from this revision together. The game runs on the laptop/Render; the Pico receives BLE advertisements and forwards normalized USB input. These are BLE manufacturer broadcasts, not Bluetooth HID devices: do not pair the remotes in macOS Bluetooth settings.

## What was broken

- The ESP32 sketches sent 7-byte changes only. Losing a center/direction message left the receiver with an incorrect held state; no snapshot could repair it.
- Direction, tilt, and gestures shared a queue with 240 ms per event, causing delayed/stale input.
- The receiver updated its freshness timer before rejecting duplicate/old sequences. A rebooted remote could remain apparently connected while its data was ignored.
- `if (!BLE.begin(...))` does not compile with the installed Arduino-Pico 6.3.0 API (`begin` returns void).
- Multiple `.ino` files in one Arduino sketch folder can be compiled together. Each board now has a separate folder.

## Firmware in this folder

- `ESPController1/ESPController1.ino`: player 1, ESP32, MPU6050.
- `ESPController2/ESPController2.ino`: player 2, ESP32, MPU9250.
- `RPPicoCentralHub/RPPicoCentralHub.ino` and `ControllerProtocol.h`: Pico 2 W receiver.
- `Test Pico Bluetooth` is an old diagnostic only. Its human-readable output does not control the game. Do not flash it as the game hub.
- `AstroLab_Pico_Game_Bridge_Fixed.zip` contains the current matching set, not just the old receiver.

## Flashing order

1. Stop the laptop game bridge and close all Arduino Serial Monitors.
2. Open **only** `ESPController1/ESPController1.ino`. Select your ESP32 board/port (compiled here as ESP32 Dev Module, Espressif core 3.3.12). Upload. Keep the stick centered and remote still for the first two seconds after reset.
3. Repeat for `ESPController2/ESPController2.ino`. The player IDs must be different; do not flash P1 onto both remotes. Pins remain SDA 21, SCL 22, joystick X 34/Y 35, button 25.
4. Open `RPPicoCentralHub/RPPicoCentralHub.ino`; keep its header beside it. Select **Raspberry Pi Pico 2 W** in Earle Philhower's **Raspberry Pi RP2040/RP2350** package, version 6.3.0. Select **IP/Bluetooth Stack → IPv4 + Bluetooth** and leave the OS at the default No OS. Upload by USB. If necessary, hold BOOTSEL while connecting to enter upload mode.
   Alternatively, the compiled `firmware/RPPicoCentralHub.uf2` is for **Pico 2 W only**: hold BOOTSEL while plugging it into USB, then copy that file onto the boot drive. It reboots automatically. This replaces only the Pico program; both ESP32s still need their uploads.
5. Power/restart both remotes, centered and still. Keep the Pico attached to the laptop using a USB data cable.

Do not swap the two MPU sensor definitions. If the IMU fails, joystick/button input still works, but tilt/shake/flick cannot work until the I2C wiring/sensor is fixed.

## Check USB before opening the game

Open the **Pico's** Serial Monitor at 115200. With both remotes powered, expect repeating lines about every 50 ms:

```
REMOTE,P1,STATE,0.00,0.00,0.00
REMOTE,P2,STATE,0.00,0.00,0.00
```

Fields are **forward/reverse, left/right steering, left/right tilt**. Push P1 forward: the first number becomes positive. Center it: it returns to zero. Click: `REMOTE,P1,SELECT` once. Shake: `SHAKE`; upward flick: `UPWARD_FLICK`. Disconnect a remote: neutral state then `DISCONNECTED` after about half a second. Reconnect: current axes recover without replaying the last button/gesture.

If only `ASTROLAB,READY` appears, check both ESP uploads, player IDs, power, and the Pico Bluetooth build setting. Do not diagnose this as a website issue yet. **Close Serial Monitor before starting Python**; only one program should own the Pico USB port.

## Connect to the deployed website

Keep the laptop game checkout on **space-odyssey-deploy**, not Hardware (Hardware contains firmware only). Pull its latest commit. Find the Pico port:

```sh
ls /dev/cu.usbmodem*
```

Open https://spaceodyssey.work in Chrome. Expand **Controller & camera setup** and copy the pairing code. From the game repository run:

```sh
backend/.venv/bin/python start_game.py --no-camera --cloud https://spaceodyssey.work --serial /dev/cu.usbmodemXXXX
```

Replace the example port with your actual Pico port. Paste the pairing code when prompted (the prompt hides input). Keep that terminal running. If port 8000 is already in use, stop the old bridge or append `--port 8002`. If you refresh the website, restart the launcher with its new pairing code.

The website alone cannot read the USB Pico. The laptop bridge is required. `--no-camera` avoids opening the Python camera when using the website's **Open motion camera → Enable camera** in Chrome. Keep that preview on the laptop and move the game to the HDMI monitor.

## .env: do not reset or delete it

Keep your Gemini key and existing settings. The launcher above sets physical USB mode and the serial port itself. If you run the backend directly instead, set these in **local** `backend/.env`:

```ini
SIMULATE_PICO=false
SERIAL_PORT=/dev/cu.usbmodemXXXX
VISION_ENABLED=false
SPACE_ODYSSEY_HOSTED=false
```

For an inverted axis, only change the applicable local setting to `-1`, then restart the bridge:
`P1_FORWARD_SIGN`, `P1_STEER_SIGN`, `P1_TILT_SIGN`, or P2 equivalents. Defaults are `1`. Do not put a USB path into Render's environment or disable hosted mode there.

P1 joystick = forward/reverse at constant height and left/right steering. P2 tilt = roll stabilization. Minigames retain their own mappings. The screen cursors show raw joystick readings; the expanded panel shows applied signs/game input.

## Protocol and verification

Manufacturer bytes: `FF FF 41 4C player action sequence forward steer tilt` (10 bytes). Player is ASCII `1`/`2`; axes are signed percentages -100..100. Each new transmission gets a modulo-256 sequence. Idle snapshots refresh every 80 ms; discrete actions are advertised for 160 ms. The Pico suppresses duplicates/out-of-order reports, neutralizes stale state after 500 ms, and forwards no queued radio input older than 200 ms. Event queues drop gestures older than 300 ms. Seven-byte input remains decodable for diagnostics but lacks recoverable state: reflash the ESPs for reliable operation.

Host tests cover snapshot recovery, center, duplicates, out-of-order sequences, wraparound, remote reboot, frozen advertisements, malformed packets, and the actual game parser. Physical radio range, ADC wiring, and gesture sensitivity must still be checked on the boards.

```sh
c++ -std=c++11 -Wall -Wextra -Werror hardware/tests/controller_protocol.cpp -o /tmp/odyssey-protocol-test
/tmp/odyssey-protocol-test
/path/to/game/backend/.venv/bin/python hardware/tests/verify_game_bridge.py /path/to/game /tmp/odyssey-protocol-test
```

Build verification: all three sketches compiled successfully with ESP32 core 3.3.12 / Arduino-Pico 6.3.0; 128 backend tests passed. No boards were flashed by this change, and no Pico serial device was connected during verification.

## Current update: MPU diagnostics and sensitive flick

Flash **both ESP32s and the Pico** from this revision for the MPU data tab. The extended 23-byte BLE snapshot adds IMU health plus six signed 16-bit readings scaled by 100 (acceleration m/s² and gyro rad/s). Old 7/10-byte snapshots still work but cannot show MPU diagnostics. Flick threshold is now 5.0 m/s², with a 1.8 release threshold. Joystick readings use median filtering and a smooth dead zone.

Open Controller setup / MPU sensor data in the game. IMU READ FAILED means the sensor cannot be read; changing game settings cannot repair disconnected I2C wiring. Check the sensor power, ground, SDA21/SCL22 and 0x68/0x69 address. Tilt up triggers jump, joystick forward holds duck in appropriate games, and returning to center releases it. Left/right tilt remains flight roll for P2.

Camera tracking is optional. The launcher defaults to remotes only; pass `--camera` to open the laptop OpenCV preview, or use the website's Open motion camera button in Chrome. Only movement events are forwarded, not camera images. Keep the Pico connected to the laptop and pair the current website code after restarting the launcher.

Planet log saves the first **completed** round per planet for this session. Leaving early does not assign a win. Replays keep the original result; restarting/exiting the game clears it. The modest higher-gravity jump bonus is a visual arcade effect only, not a physics simulation.
