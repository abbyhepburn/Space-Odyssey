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

    def update(self, pose: BodyPose, now: float):
        self.last_seen = now
        if not math.isfinite(pose.shoulder_y) or not math.isfinite(pose.hip_y):
            return []
        torso = pose.hip_y - pose.shoulder_y
        if pose.confidence < 0.55 or torso < 0.07:
            return []
        if self.baseline is None:
            # Only calibrate from upright, roughly extended legs.
            if pose.knee_angle >= 155:
                self.calibration.append(pose)
                if len(self.calibration) >= self.calibration_frames:
                    self.baseline = (
                        mean(p.shoulder_y for p in self.calibration),
                        mean(p.hip_y for p in self.calibration),
                        max(0.07, mean(p.hip_y - p.shoulder_y for p in self.calibration)),
                    )
                    self.shoulder_filtered = pose.shoulder_y
                    self.hip_filtered = pose.hip_y
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
            self.jumping = True
            self.last_jump = now
            events.append('JUMP')

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
    """Players stay on their assigned half. No identity assumptions across sides."""
    def __init__(self, **detector_settings):
        self.detectors = [MovementDetector(**detector_settings), MovementDetector(**detector_settings)]

    @property
    def ready(self):
        return all(detector.ready for detector in self.detectors)

    def reset(self):
        for detector in self.detectors:
            detector.reset()

    def process(self, poses: list[BodyPose], now: float):
        groups = [[], []]
        for pose in poses:
            # A narrow center dead zone helps avoid accidental player swaps.
            if pose.center_x < 0.47:
                groups[0].append(pose)
            elif pose.center_x > 0.53:
                groups[1].append(pose)
        events = []
        for index, candidates in enumerate(groups):
            if len(candidates) == 1:
                actions = self.detectors[index].update(candidates[0], now)
            else:
                actions = self.detectors[index].lost(now)
            events.extend((f'P{index + 1}', action) for action in actions)
        return events
