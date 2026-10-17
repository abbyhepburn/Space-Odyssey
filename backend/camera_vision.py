"""Standalone iPhone/USB/Mac camera preview -> Space Odyssey game backend.

Run in a separate terminal on the MacBook. Video stays LOCAL; only movement
signals reach FastAPI. Use `python camera_vision.py --scan` to find camera index.

Keyboard in camera preview: C = recalibrate both players, Q/ESC = quit.
"""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pose_movements import BodyPose, TwoPlayerTracker
from download_pose_model import MODEL_PATH

POSE_CONNECTIONS = (
    (11, 12), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
    (24, 26), (26, 28), (27, 29), (28, 30),
)


class GameBridge:
    """Network work in another thread so camera frames never wait on HTTP."""
    def __init__(self, backend: str):
        backend = backend.rstrip('/')
        if backend not in ('http://127.0.0.1:8000', 'http://localhost:8000'):
            raise ValueError('For safety, backend must be local: http://127.0.0.1:8000')
        self.backend = backend
        self.messages = queue.Queue(maxsize=80)
        self.stop = threading.Event()
        self.connected = False
        self.errors = 0
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def post(self, path, data):
        try:
            self.messages.put_nowait((path, data))
        except queue.Full:
            # Never block the live camera on a disconnected backend.
            if path.endswith('/event'):
                print('Warning: backend is too slow; camera event dropped', file=sys.stderr)

    def event(self, player, action):
        print(f'CAMERA EVENT: {player} {action}', flush=True)
        self.post('/api/vision/event', {'player': player, 'action': action})

    def heartbeat(self, ready, detail):
        self.post('/api/vision/heartbeat', {'ready': bool(ready), 'detail': detail[:120]})

    def _worker(self):
        while not self.stop.is_set() or not self.messages.empty():
            try:
                path, data = self.messages.get(timeout=0.1)
            except queue.Empty:
                continue
            payload = json.dumps(data).encode('utf-8')
            req = Request(self.backend + path, data=payload,
                          headers={'Content-Type': 'application/json'}, method='POST')
            try:
                with urlopen(req, timeout=0.8) as response:
                    self.connected = response.status == 200
                self.errors = 0
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                self.connected = False
                self.errors += 1
                if self.errors == 1 or self.errors % 30 == 0:
                    print(f'Backend unavailable: {exc}. Start uvicorn on port 8000.',
                          file=sys.stderr)
            finally:
                self.messages.task_done()

    def close(self):
        # Graceful duck release (best effort) before stopping.
        self.event('P1', 'DUCK_OFF')
        self.event('P2', 'DUCK_OFF')
        self.heartbeat(False, 'Camera stopped')
        self.stop.set()
        self.thread.join(timeout=2)


def open_camera(cv2, index, width=960, height=540):
    source = int(index) if str(index).isdigit() else index
    if sys.platform == 'darwin' and isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
    else:
        cap = cv2.VideoCapture(source)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def camera_scan(cv2):
    print('Camera indices visible to OpenCV (not necessarily the same order as FaceTime):')
    found = []
    for index in range(8):
        cap = open_camera(cv2, index, 640, 360)
        try:
            if cap.isOpened():
                ok, frame = cap.read()
                if ok and frame is not None:
                    found.append(index)
                    print(f'  Camera {index}: {frame.shape[1]}x{frame.shape[0]}')
        finally:
            cap.release()
    print('Available indices:', found or 'none. Check macOS Camera permissions / Continuity Camera.')
    print('If iPhone is not listed, try USB, relaunch Terminal, or a virtual camera app.')


def knee_angle(pose, hip, knee, ankle):
    import math
    a = (pose[hip].x - pose[knee].x, pose[hip].y - pose[knee].y)
    b = (pose[ankle].x - pose[knee].x, pose[ankle].y - pose[knee].y)
    denom = math.hypot(*a) * math.hypot(*b)
    if denom < 1e-7:
        return 180.0
    dot = max(-1.0, min(1.0, (a[0]*b[0]+a[1]*b[1]) / denom))
    return math.degrees(math.acos(dot))


def extract_body_pose(landmarks):
    ids = (11, 12, 23, 24, 25, 26, 27, 28)
    confidence = min(getattr(landmarks[i], 'visibility', 1.0) for i in ids)
    shoulder = (landmarks[11].y + landmarks[12].y) / 2
    hip = (landmarks[23].y + landmarks[24].y) / 2
    x = (landmarks[11].x + landmarks[12].x) / 2
    knee = (knee_angle(landmarks, 23, 25, 27) +
            knee_angle(landmarks, 24, 26, 28)) / 2
    return BodyPose(x, shoulder, hip, knee, confidence)


def overlay(cv2, frame, landmarks, tracker, bridge):
    height, width = frame.shape[:2]
    mid = width // 2
    cv2.line(frame, (mid, 0), (mid, height), (180, 180, 180), 2)
    for index, det in enumerate(tracker.detectors):
        color = (255, 175, 80) if index == 0 else (80, 220, 255)
        label = f'P{index + 1}: ' + (
            'CALIBRATE (STAND STILL)' if not det.ready else
            'JUMP' if det.jumping else 'DUCK' if det.ducking else 'READY')
        cv2.putText(frame, label, (16 + index * mid, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        if not det.ready:
            cv2.putText(frame, f'{round(det.progress*100)}%',
                        (16 + index * mid, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    for pose in landmarks:
        body = extract_body_pose(pose)
        if 0.47 <= body.center_x <= 0.53:
            continue
        color = (255, 175, 80) if body.center_x < 0.5 else (80, 220, 255)
        for a, b in POSE_CONNECTIONS:
            cv2.line(frame, (int(pose[a].x*width), int(pose[a].y*height)),
                     (int(pose[b].x*width), int(pose[b].y*height)), color, 2)
        for i in (11, 12, 23, 24, 25, 26, 27, 28):
            cv2.circle(frame, (int(pose[i].x*width), int(pose[i].y*height)), 5, color, -1)
    status = ('CAMERA ONLY' if bridge is None else 'BACKEND CONNECTED' if bridge.connected else 'BACKEND OFFLINE')
    cv2.putText(frame, f'{status}   C: recalibrate   Q: quit', (14, height - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (110, 240, 120) if bridge and bridge.connected else
                (180, 180, 255), 2)


def run(args):
    import cv2
    import mediapipe as mp
    if args.scan:
        camera_scan(cv2)
        return
    model = Path(args.model)
    if not model.is_file():
        raise FileNotFoundError(f'Missing {model}. Run: python download_pose_model.py')
    cap = open_camera(cv2, args.camera, args.width, args.height)
    if not cap.isOpened():
        raise RuntimeError('Camera could not be opened. Try --scan, or --camera 0 / --camera 1.')
    bridge = None if args.no_send else GameBridge(args.backend)
    tracker = TwoPlayerTracker(calibration_frames=args.calibration_frames,
                               jump_ratio=args.jump_ratio, duck_ratio=args.duck_ratio)
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.55,
        min_pose_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )
    started = time.monotonic()
    last_stamp = -1
    last_heartbeat = -1e6
    missed = 0
    print('Camera active. Stand upright in your own half until both labels read READY.')
    print('P1 is LEFT in the preview, P2 RIGHT. C = recalibrate; Q/ESC = quit.')
    try:
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    missed += 1
                    if missed > 20:
                        raise RuntimeError('Camera feed lost. Reconnect iPhone and restart.')
                    time.sleep(0.06)
                    continue
                missed = 0
                if args.mirror:
                    frame = cv2.flip(frame, 1)
                now = time.monotonic()
                stamp = max(last_stamp + 1, int((now - started)*1000))
                last_stamp = stamp
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(image, stamp)
                detected = [extract_body_pose(p) for p in result.pose_landmarks]
                events = tracker.process(detected, now)
                for player, action in events:
                    if bridge:
                        bridge.event(player, action)
                    else:
                        print('LOCAL TEST:', player, action)
                if bridge and now-last_heartbeat >= 1.5:
                    bridge.heartbeat(tracker.ready, 'P1/P2 shoulders tracked')
                    last_heartbeat = now
                overlay(cv2, frame, result.pose_landmarks, tracker, bridge)
                cv2.imshow('SPACE ODYSSEY | Camera Tracking (MacBook)', frame)
                key = cv2.waitKey(1) & 0xff
                if key in (ord('q'), 27):
                    break
                if key == ord('c'):
                    tracker.reset()
                    if bridge:
                        bridge.event('P1', 'DUCK_OFF')
                        bridge.event('P2', 'DUCK_OFF')
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if bridge:
            bridge.close()


def main():
    parser = argparse.ArgumentParser(description='Space Odyssey two-player MediaPipe camera')
    parser.add_argument('--scan', action='store_true', help='Find accessible cameras')
    parser.add_argument('--camera', default='0', help='OpenCV camera index, or video source URL')
    parser.add_argument('--model', default=str(MODEL_PATH))
    parser.add_argument('--backend', default='http://127.0.0.1:8000')
    parser.add_argument('--width', type=int, default=960)
    parser.add_argument('--height', type=int, default=540)
    parser.add_argument('--calibration-frames', type=int, default=40)
    parser.add_argument('--jump-ratio', type=float, default=0.22)
    parser.add_argument('--duck-ratio', type=float, default=0.25)
    parser.add_argument('--mirror', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--no-send', action='store_true', help='Camera-only test, no backend')
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
