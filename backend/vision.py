"""Optional two-person MediaPipe Tasks worker; normalized inputs only, never serial."""
import os
import threading
import time
import math

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
        cap=None
        try:
            import cv2
            import mediapipe as mp
            options=mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=os.getenv('POSE_MODEL_PATH','pose_landmarker_lite.task')),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=2)
            cap=cv2.VideoCapture(int(os.getenv('CAMERA_INDEX','0')))
            if not cap.isOpened(): raise RuntimeError('Camera not found')
            detectors=[Detector(),Detector()]; last_seen=[0,0]; prior=[None,None]; stamp=0
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
                while not self.stop_event.is_set():
                    ok, frame=cap.read()
                    if not ok: raise RuntimeError('Camera frame unavailable')
                    if self.recalibrate.is_set():
                        detectors=[Detector(),Detector()]; self.recalibrate.clear()
                        for player in ('P1','P2'): self.send(f'INPUT,{player},DUCK_OFF')
                    now=time.monotonic(); stamp=max(stamp+1,int(now*1000))
                    result=landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),stamp)
                    groups=[[],[]]; warning='Stand upright for 45 frames. Keep your assigned side.'
                    for pose in result.pose_landmarks:
                        x=(pose[23].x+pose[24].x)/2
                        if min(pose[j].visibility for j in (11,12,23,24,25,26,27,28))<.65: continue
                        side=0 if x<.5 else 1; groups[side].append((x,pose))
                    for i, group in enumerate(groups):
                        if len(group)!=1 or abs(group[0][0]-.5)<.07:
                            if detectors[i].duck: self.send(f'INPUT,P{i+1},DUCK_OFF')
                            detectors[i]=Detector(); prior[i]=None
                            warning='Pose missing / center crossing. Return to assigned sides and recalibrate.'
                            continue
                        x,pose=group[0]
                        if prior[i] is not None and abs(x-prior[i])>.18:
                            detectors[i]=Detector(); warning='Possible side swap — recalibrating. P1 left, P2 right.'
                        prior[i]=x; last_seen[i]=now
                        hip=(pose[23].y+pose[24].y)/2; ankle=(pose[27].y+pose[28].y)/2
                        def angle(a,b,c):
                            u=(a.x-b.x,a.y-b.y); v=(c.x-b.x,c.y-b.y)
                            return math.degrees(math.acos(max(-1,min(1,sum(u[j]*v[j] for j in (0,1))/(math.hypot(*u)*math.hypot(*v)+1e-8)))))
                        knee=(angle(pose[23],pose[25],pose[27])+angle(pose[24],pose[26],pose[28]))/2
                        for action in detectors[i].update(hip,ankle,knee,now): self.send(f'INPUT,P{i+1},{action}')
                        if self.debug:
                            h,w=frame.shape[:2]
                            for a,b in ((11,12),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28)):
                                cv2.line(frame,(int(pose[a].x*w),int(pose[a].y*h)),(int(pose[b].x*w),int(pose[b].y*h)),(80,240,180),2)
                            cv2.putText(frame,f'P{i+1}',(int(x*w),50),cv2.FONT_HERSHEY_SIMPLEX,1,(80,240,180),2)
                    ready=all(d.baseline is not None for d in detectors)
                    self.status(ready,'Tracking P1 left / P2 right' if ready else warning)
                    if self.debug:
                        cv2.putText(frame,'P1 LEFT | P2 RIGHT — C: calibrate', (12,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
                        cv2.imshow('Space Odyssey — pose debug',frame)
                        if cv2.waitKey(1)&0xff==ord('c'): self.recalibrate.set()
                    else: cv2.destroyAllWindows()
        except Exception as exc: self.status(False,f'Vision unavailable: {exc}. Demo controls remain available.')
        finally:
            self.status(False,'Vision stopped — demo controls available')
            for player in ('P1','P2'): self.send(f'INPUT,{player},DUCK_OFF')
            if cap is not None: cap.release()
            try:
                import cv2
                cv2.destroyAllWindows()
            except ImportError: pass
