<div align="center">

# 🚀 SPACE ODYSSEY

### Two explorers. One spacecraft. An entire universe to discover.

**A cooperative, AI-powered space adventure controlled by two custom-built wireless motion remotes.**

[**Play Space Odyssey**](https://spaceodyssey.work) · [**Source code**](https://github.com/abbyhepburn/Space-Odyssey)

</div>

![Space Odyssey title screen, with the Initiate Launch button and orbital spacecraft visuals](docs/images/space-odyssey-title-screen.png)

## 🌌 About the project

**Space Odyssey** brings the excitement of motion-controlled games to a two-player journey through the solar system. Instead of conventional gamepads, players pilot a spacecraft using **hand-built ESP32 controllers** with motion sensors, analog joysticks, and buttons.

Players explore planetary environments, take on themed challenges, and cooperate as a two-person crew. **Google Gemini** helps create planet-themed mission content, while the game uses defined gameplay mechanics to turn those missions into playable challenges.

> **Current controls:** Space Odyssey uses the two physical handheld remotes. Webcam tracking, jumping, and ducking are **not** part of the current gameplay experience.

## 🎮 In-game preview

![Space Odyssey in-game cockpit showing Earth, the planetary log, speed, and player-specific controls](docs/images/space-odyssey-gameplay.png)

*Inside the spacecraft: P1 controls flight using a joystick, while P2 tilts their remote to level the ship. Both controllers appear in the live status panel.*

## 🕹️ How to play

Each player uses a custom wireless remote. The game uses different inputs depending on the current challenge.

| Input | Example role |
| --- | --- |
| **Joystick** | Fly, steer, and navigate menus |
| **Tilt left / right** | Balance or level the spacecraft |
| **Shake** | Interact with obstacles, including asteroid challenges |
| **Flick upward** | Trigger special in-game actions |
| **Joystick button** | Select or activate a context-dependent action |

Two-player cooperation is central to the experience: the crew shares the journey, and each player can be assigned a different control task.

## ⚙️ How it works

```text
Controller 1: ESP32 + MPU6050-compatible IMU + joystick
                                        \
                                         BLE advertisements
                                        / 
Controller 2: ESP32 + MPU9250 IMU + joystick
                    |
                    v
            Raspberry Pi Pico 2 W
                    |
                USB serial
                    |
              Python backend
                    |
       Game state / cloud integration
                    |
         React + Three.js frontend
```

- **Custom controllers:** Arduino C++ firmware reads I²C motion sensors and joystick input, detects gestures, and broadcasts controller updates over Bluetooth Low Energy (BLE).
- **Pico 2 W bridge:** Receives both controllers' BLE advertisements and forwards decoded events and controller state over USB serial.
- **Python backend:** Processes controller messages and bridges physical inputs to the game.
- **3D frontend:** React, Vite, Three.js, and React Three Fiber render the space environment and flight UI.
- **Generative AI:** Google Gemini provides planet-themed mission content through a constrained mission system.

## 🧰 Built with

| Area | Technologies |
| --- | --- |
| Firmware & hardware | ESP32, Raspberry Pi Pico 2 W, MPU6050-compatible IMU, MPU9250, analog joysticks, Arduino C++, I²C |
| Wireless and serial | Bluetooth Low Energy advertising, USB serial |
| Backend | Python |
| Frontend & 3D | JavaScript, React, Vite, Three.js, React Three Fiber |
| AI | Google Gemini API |
| Development | Git, GitHub, VS Code, Arduino IDE |

## 💻 Local setup

The game has a deployed frontend at **[spaceodyssey.work](https://spaceodyssey.work)**. Running physical controllers still requires a local computer connected to the Pico 2 W and the project's Python bridge.

### Prerequisites

- Git and a local clone of this repository
- Node.js and npm, if running the frontend locally
- Python and the dependencies specified by `backend/requirements.txt` (Python **3.12** is a useful choice for compatibility with older pinned dependencies)
- A Pico 2 W with the appropriate BLE receiver firmware, connected by USB
- Two programmed ESP32 motion controllers
- A Gemini API key for AI-backed mission features

### 1. Set up Python

From the repository root on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If `py -3.12` cannot find an interpreter, install Python 3.12 first. Using a virtual environment is recommended because newer Python releases may not have compatible prebuilt wheels for all pinned dependencies.

### 2. Configure environment variables

Create a **`.env`** file in the location expected by the backend configuration loader. Example values:

```dotenv
SIMULATE_PICO=false
SERIAL_PORT=COM6
VISION_ENABLED=false
GEMINI_API_KEY=YOUR_PRIVATE_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
```

Set `SERIAL_PORT` to the Pico's actual port (`COM6` is **only an example**). On macOS, the device name may look like `/dev/cu.usbmodem...`.

**Never commit `.env` or expose API keys in screenshots.** If a key has been shared publicly, revoke and replace it.

### 3. Start the hardware bridge

Your team's demonstrated launcher command has this form:

```powershell
python start_game.py --cloud https://spaceodyssey.work --serial COM6 --port 6021
```

Run this from the **directory that actually contains `start_game.py`**, using Python from your virtual environment. For example, if the launcher is at the repository root:

```powershell
.\.venv\Scripts\python.exe .\start_game.py --cloud https://spaceodyssey.work --serial COM6 --port 6021
```

The `--port` option is the local service port, **not** the Pico's COM port. Keep the Arduino Serial Monitor closed while the Python program owns the Pico serial connection.

> **Maintainer note:** Confirm the launcher's file location and supported flags against the current branch before finalizing this section; repository files were not available for independent verification when this README was prepared.

### 4. Optional: start the web frontend locally

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, typically `http://localhost:5173/`. To play the deployed game instead, open [spaceodyssey.work](https://spaceodyssey.work).

## 🔧 Controller debugging

If a controller does not respond:

1. Confirm its ESP32 firmware is uploaded and the Pico bridge is running.
2. Check that the Pico appears on the expected USB serial port and that no other application has opened it.
3. On the ESP32, verify that the motion sensor is detected over I²C: **SDA → GPIO21, SCL → GPIO22**, with 3.3 V and common ground.
4. Check serial diagnostics for changing accelerometer readings, shake/flick detections, and transmitted BLE packets.
5. Verify that the Pico forwards `REMOTE,P1,...` and `REMOTE,P2,...` messages to the Python backend.

## 🧩 Challenges and lessons

- **Mixed motion sensors:** Integrating two different IMUs and working with direct I²C registers when a sensor library did not initialize a device correctly.
- **Gesture recognition:** Distinguishing shaking from flicking, filtering noise, and calibrating motion thresholds.
- **Wireless reliability:** Handling BLE advertisement loss, packet sequencing, and state recovery for responsive steering.
- **Full-stack integration:** Connecting ESP32 firmware, a Pico receiver, Python, and a real-time 3D web experience.

## ✨ What's next

More planetary challenges, tighter cooperative mechanics, refined gesture detection, and improved controller enclosures.

---

<div align="center">

**SPACE ODYSSEY — Two pilots. One mission.** 🪐

Built for **SwampHacks XII**.

</div>
