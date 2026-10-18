# Deploy Space Odyssey to spaceodyssey.work

This is a React build served by a persistent FastAPI/WebSocket process. Render's Docker web service runs both together. Each browser gets an isolated two-player game; a paired laptop forwards USB controller input.

1. Push this version to GitHub, then open https://dashboard.render.com/select-repo?type=blueprint and select abbyhepburn/Space-Odyssey and the deployment branch.
2. Render reads `render.yaml`. Review the Free service, then provide GEMINI_API_KEY in Render's secret environment field. Never put the key in frontend code or Git. The configured model is gemini-2.5-flash; change it to a model enabled for your key if necessary.
3. Deploy. Wait for the health check and the generated onrender.com URL to work. No domain is live merely because the build succeeds locally.
4. In the Render service's Settings → Custom Domains, verify spaceodyssey.work. The blueprint already requests this domain.
5. In GoDaddy DNS for spaceodyssey.work, copy the EXACT A/CNAME targets Render shows. Replace only conflicting web records for @ / www; preserve mail MX/TXT records. Return to Render and Verify. Wait for its HTTPS certificate to become ready.
6. Test https://spaceodyssey.work: launch, visit a planet, start a challenge, verify both players score separately. Free hosting can sleep when idle; wake it before a presentation.

Official instructions: https://render.com/docs/blueprint-spec and https://render.com/docs/custom-domains

## Physical controllers on the deployed game

The hosting server cannot open the laptop webcam or USB port. Use the included outbound pairing bridge:

- Open the online game, expand **Controller setup**, and copy its pairing code.
- From the repository, activate backend/.venv, then run:

```sh
python start_game.py --cloud https://spaceodyssey.work --serial /dev/cu.usbmodemYOUR_PICO
```

Paste the code at the hidden prompt. No camera is used: tilt each remote up to jump and push its joystick forward to duck. The online browser may be fullscreen on the HDMI monitor. Reloading the online game creates a new game and pairing code; restart the launcher to pair again. Run one Render worker/instance because sessions are in memory.

For keyboard-only play, no laptop bridge is needed. P1: A/D steer, F/S forward/reverse, Space jump, C duck, Q shake, R flick, E select. P2: arrows steer, I jump, K duck, U shake, P flick, O select.

## Known validation limits

The automated tests cover isolated hosted sessions, pairing, camera event routing, input expiry, scoring, and timing. Actual ESP/Pico firmware compilation/flashing and two-person camera movement need physical verification. Live Gemini verification timed out during this update; supported local action challenges remain available and their source is labeled honestly. Deployment and DNS require the owner's Render/GoDaddy accounts; no production deployment has yet been verified.
