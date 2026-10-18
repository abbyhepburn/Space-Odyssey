"""Optional two-person MediaPipe Tasks worker; normalized inputs only, never serial."""
import os
import threading
import time
import math
from download_pose_model import MODEL_PATH

class Detector:
    def __init__(self):
        self.samples=[]; self.baseline=None; self.air=False; self.duck=False
        self.last_jump=-10; self.pending=None; self.since=0
    def update(self, hip, ankle, knee_angle, now):
        if self.baseline is None:
            self.samples.append((hip,ankle))
            if len(self.samples)>=45:
                self.baseline=tuple(sum(x[i] for x in self.samples)/len(self.samples) for i in (0,1))
            return []
        h,a=self.baseline; events=[]
        if self.air and hip>h-.025 and ankle>a-.02: self.air=False
        if not self.air and not self.duck and now-self.last_jump>.85 and h-hip>float(os.getenv('JUMP_RISE','.055')) and a-ankle>.025:
            events.append('JUMP'); self.air=True; self.last_jump=now
        want = hip-h>float(os.getenv('DUCK_DROP','.09')) and knee_angle<150
        if self.duck: want=not (hip-h<.045 and knee_angle>155)
        if want!=self.duck:
            if self.pending!=want: self.pending=want; self.since=now
            elif now-self.since>.18:
                self.duck=want; events.append('DUCK_ON' if want else 'DUCK_OFF'); self.pending=None
        else: self.pending=None
        return events

class VisionWorker(threading.Thread):
    def __init__(self, send, status):
        super().__init__(daemon=True); self.send=send; self.status=status; self.stop_event=threading.Event()
        self.debug=os.getenv('VISION_DEBUG','false').lower()=='true'
        self.recalibrate=threading.Event()
    def close(self): self.stop_event.set(); self.join(timeout=3)
    def run(self):
        cap=None;failed=False
        try:
            import cv2
            import mediapipe as mp
            options=mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=os.getenv('POSE_MODEL_PATH',str(MODEL_PATH))),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=2)
            cap=cv2.VideoCapture(int(os.getenv('CAMERA_INDEX','0')))
            if not cap.isOpened(): raise RuntimeError('Camera not found')
            from pose_movements import TwoPlayerTracker
            from camera_vision import extract_body_pose, overlay
            # Same detector and player assignment as the standalone OpenCV path.
            tracker=TwoPlayerTracker(shoulder_only=True);stamp=0;last_status=0.;last_held=0.
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
                while not self.stop_event.is_set():
                    ok,frame=cap.read()
                    if not ok:raise RuntimeError('Camera frame unavailable')
                    frame=cv2.flip(frame,1) # P1 left / P2 right in mirrored preview.
                    if self.recalibrate.is_set():
                        tracker.reset();self.recalibrate.clear()
                        for player in ('P1','P2'):self.send(f'INPUT,{player},DUCK_OFF')
                    now=time.monotonic();stamp=max(stamp+1,int(now*1000))
                    image=mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
                    result=landmarker.detect_for_video(image,stamp)
                    for player,action in tracker.process([extract_body_pose(p) for p in result.pose_landmarks],now):
                        self.send(f'INPUT,{player},{action}')
                    if now-last_held>=.3:
                        for i,detector in enumerate(tracker.detectors):
                            self.send(f'INPUT,P{i+1},'+('DUCK_ON' if detector.ducking else 'DUCK_OFF'))
                        last_held=now
                    if now-last_status>=.5:
                        self.status(tracker.ready,'Tracking shoulders: P1 left / P2 right' if tracker.ready else 'Keep both players’ shoulders visible in their own half')
                        last_status=now
                    if self.debug:
                        overlay(cv2,frame,result.pose_landmarks,tracker,None)
                        cv2.imshow('Space Odyssey — pose debug',frame)
                        key=cv2.waitKey(1)&0xff
                        if key==ord('c'):self.recalibrate.set()
                        if key in (ord('q'),27):break
        except Exception as exc:
            failed=True;self.status(False,f'Vision unavailable: {exc}. Demo controls remain available.')
        finally:
            if not failed:self.status(False,'Vision stopped — demo controls available')
            for player in ('P1','P2'): self.send(f'INPUT,{player},DUCK_OFF')
            if cap is not None: cap.release()
            try:
                import cv2
                cv2.destroyAllWindows()
            except ImportError: pass
