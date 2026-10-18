"""Pure Python two-player shoulder/hip jump + duck state machines.

Camera image coordinates: y increases DOWN. Normalize motion to each player's
standing shoulder-to-hip torso length so camera distance affects thresholds less.
No video, landmarks, or personal calibration data are stored.
"""
from dataclasses import dataclass, field
import math
from statistics import mean


@dataclass(frozen=True)
class BodyPose:
    center_x: float
    shoulder_y: float
    hip_y: float
    knee_angle: float
    confidence: float = 1.0


@dataclass
class MovementDetector:
    shoulder_only: bool = False
    calibration_frames: int = 40
    jump_ratio: float = 0.22
    duck_ratio: float = 0.25
    jump_cooldown: float = 0.75
    duck_hold: float = 0.16
    baseline: tuple[float, float, float] | None = None
    calibration: list[BodyPose] = field(default_factory=list)
    shoulder_filtered: float | None = None
    hip_filtered: float | None = None
    jumping: bool = False
    ducking: bool = False
    pending_duck: bool | None = None
    pending_since: float = 0.0
    last_jump: float = -1e6
    last_duck_release: float = -1e6
    last_seen: float = -1e6
    pending_jump_since: float | None = None

    @property
    def ready(self):
        return self.baseline is not None

    @property
    def progress(self):
        return min(1.0, len(self.calibration) / self.calibration_frames)

    def reset(self):
        self.baseline = None
        self.calibration.clear()
        self.shoulder_filtered = None
        self.hip_filtered = None
        self.jumping = False
        self.ducking = False
        self.pending_duck = None
        self.pending_jump_since = None

    def lost(self, now: float):
        """Release held duck after momentary loss; recalibrate after long absence."""
        events = []
        duration = now - self.last_seen
        if duration > 0.65 and self.ducking:
            self.ducking = False
            self.pending_duck = None
            self.last_duck_release = now
            events.append('DUCK_OFF')
        if duration > 3.0 and self.ready:
            self.reset()
        return events

    def shoulder_update(self, pose: BodyPose, now: float):
        # Immediate reference from the first visible shoulders; no standing timer,
        # knee angle, hip motion, or manual calibration is required.
        if not all(math.isfinite(v) for v in (pose.center_x,pose.shoulder_y,pose.confidence)) or pose.confidence<.55:
            return self.lost(now)
        self.last_seen=now
        if self.baseline is None:
            scale=max(.12,min(.45,pose.hip_y-pose.shoulder_y))
            self.baseline=(pose.shoulder_y,pose.hip_y,scale)
            self.shoulder_filtered=pose.shoulder_y
            return []
        self.shoulder_filtered=.45*self.shoulder_filtered+.55*pose.shoulder_y
        base,hip,scale=self.baseline
        up=(base-self.shoulder_filtered)/scale
        events=[]
        if self.jumping and up<.07:self.jumping=False
        if not self.jumping and not self.ducking and now-self.last_jump>=self.jump_cooldown and now-self.last_duck_release>=.5 and up>self.jump_ratio:
            if self.pending_jump_since is None:self.pending_jump_since=now
            elif now-self.pending_jump_since>=.045:
                self.jumping=True;self.last_jump=now;self.pending_jump_since=None;events.append('JUMP')
        else:self.pending_jump_since=None
        if self.jumping:
            self.pending_duck=None
            return events
        want=(-up>self.duck_ratio*.37) if self.ducking else (-up>self.duck_ratio)
        if want==self.ducking:self.pending_duck=None
        elif self.pending_duck!=want:self.pending_duck=want;self.pending_since=now
        elif now-self.pending_since>=self.duck_hold:
            self.ducking=want;self.pending_duck=None
            events.append('DUCK_ON' if want else 'DUCK_OFF')
            if not want:self.last_duck_release=now
        # Slowly follow neutral posture changes, never absorb a held duck/jump.
        if abs(up)<.08 and not self.ducking and self.pending_duck is None:
            self.baseline=(base*.985+self.shoulder_filtered*.015,hip,scale)
        return events

    def update(self, pose: BodyPose, now: float):
        if self.shoulder_only:return self.shoulder_update(pose,now)
        if not all(math.isfinite(v) for v in (pose.center_x,pose.shoulder_y,pose.hip_y,pose.knee_angle,pose.confidence)):
            return self.lost(now)
        torso = pose.hip_y - pose.shoulder_y
        if pose.confidence < 0.55 or torso < 0.07:
            return self.lost(now)
        self.last_seen = now
        if self.baseline is None:
            # Only calibrate from upright, roughly extended legs.
            if pose.knee_angle >= 155:
                if self.calibration and (abs(pose.shoulder_y-self.calibration[0].shoulder_y)>torso*.12 or abs(pose.hip_y-self.calibration[0].hip_y)>torso*.12):
                    self.calibration.clear()
                self.calibration.append(pose)
                if len(self.calibration) >= self.calibration_frames:
                    self.baseline = (
                        mean(p.shoulder_y for p in self.calibration),
                        mean(p.hip_y for p in self.calibration),
                        max(0.07, mean(p.hip_y - p.shoulder_y for p in self.calibration)),
                    )
                    self.shoulder_filtered = pose.shoulder_y
                    self.hip_filtered = pose.hip_y
            else:
                self.calibration.clear()
            return []

        alpha = 0.48
        self.shoulder_filtered = (1 - alpha) * self.shoulder_filtered + alpha * pose.shoulder_y
        self.hip_filtered = (1 - alpha) * self.hip_filtered + alpha * pose.hip_y
        base_shoulder, base_hip, scale = self.baseline
        shoulder_up = (base_shoulder - self.shoulder_filtered) / scale
        hip_up = (base_hip - self.hip_filtered) / scale
        shoulder_down = -shoulder_up
        hip_down = -hip_up
        events = []

        # Re-arm only after the player has landed near their standing height.
        if self.jumping and shoulder_up < 0.07 and hip_up < 0.08:
            self.jumping = False

        # Confirm jump with BOTH shoulders and hips, not arm movements alone.
        can_jump = (not self.jumping and not self.ducking and
                    now - self.last_jump >= self.jump_cooldown and
                    now - self.last_duck_release >= 0.50)
        if (can_jump and shoulder_up > self.jump_ratio and
                hip_up > self.jump_ratio * 0.62 and pose.knee_angle > 135):
            if self.pending_jump_since is None:self.pending_jump_since=now
            elif now-self.pending_jump_since>=.045:
                self.jumping = True
                self.last_jump = now
                self.pending_jump_since = None
                events.append('JUMP')
        else:
            self.pending_jump_since = None

        # Avoid interpreting the start of a jump as a duck.
        if self.jumping:
            self.pending_duck = None
            return events

        # Crouch: shoulders move down and knees bend. Require brief persistence.
        want_duck = (shoulder_down > self.duck_ratio and
                     (pose.knee_angle < 155 or shoulder_down - hip_down > 0.17))
        if self.ducking:
            # Hysteresis prevents rapid on/off while bobbing in the duck pose.
            want_duck = not (shoulder_down < self.duck_ratio * 0.37 and pose.knee_angle > 155)
        if want_duck == self.ducking:
            self.pending_duck = None
        elif self.pending_duck != want_duck:
            self.pending_duck = want_duck
            self.pending_since = now
        elif now - self.pending_since >= self.duck_hold:
            self.ducking = want_duck
            self.pending_duck = None
            if self.ducking:
                events.append('DUCK_ON')
            else:
                self.last_duck_release = now
                events.append('DUCK_OFF')
        return events


class TwoPlayerTracker:
    """Initial left/right assignment, then nearest-position continuity.

    Large jumps/ambiguous merged detections fail closed. Players should not swap
    places; after a long absence a returning player recalibrates in their lane.
    """
    def __init__(self, **detector_settings):
        self.detectors = [MovementDetector(**detector_settings), MovementDetector(**detector_settings)]
        self.positions = [None, None]
        self.visible = [False, False]

    @property
    def ready(self):
        return all(d.ready and v for d,v in zip(self.detectors,self.visible))

    def reset(self):
        for detector in self.detectors:detector.reset()
        self.positions = [None, None]
        self.visible = [False, False]

    def player_at(self, x):
        candidates=[(abs(x-p),i) for i,p in enumerate(self.positions) if p is not None and self.visible[i]]
        return min(candidates)[1] if candidates and min(candidates)[0]<.12 else None

    def process(self, poses: list[BodyPose], now: float):
        poses=[p for p in poses if p.confidence>=.55 and all(math.isfinite(v) for v in (p.center_x,p.shoulder_y,p.hip_y,p.knee_angle)) and p.hip_y-p.shoulder_y>=.07]
        assignments={};used=set();events=[]
        self.visible=[False,False]
        # Preserve identities using position continuity before assigning newcomers.
        pairs=sorted((abs(p.center_x-x),i,j) for i,x in enumerate(self.positions) if x is not None
                     for j,p in enumerate(poses) if abs(p.center_x-x)<.18)
        for distance,i,j in pairs:
            if i in assignments or j in used:continue
            # If one body is almost equidistant from two known people, wait.
            other=self.positions[1-i]
            if other is not None and abs(abs(poses[j].center_x-other)-distance)<.04:continue
            assignments[i]=j;used.add(j)
        for j,p in enumerate(poses):
            if j in used or .47<=p.center_x<=.53:continue
            i=0 if p.center_x<.5 else 1
            if self.positions[i] is None and i not in assignments:
                assignments[i]=j;used.add(j)
        for i,d in enumerate(self.detectors):
            if i in assignments:
                p=poses[assignments[i]];self.positions[i]=p.center_x;self.visible[i]=True
                actions=d.update(p,now)
            else:
                actions=d.lost(now)
                if now-d.last_seen>3.:self.positions[i]=None
            events.extend((f'P{i+1}',action) for action in actions)
        return events
