"""Run from backend: python -m pytest tests/test_pose_movements.py -q"""
from pose_movements import BodyPose, MovementDetector, TwoPlayerTracker


def pose(x=0.2, shoulder=.30, hip=.60, knee=176):
    return BodyPose(x, shoulder, hip, knee, 0.95)


def calibrated_detector():
    d = MovementDetector(calibration_frames=10)
    for i in range(10):
        assert d.update(pose(), i / 30) == []
    assert d.ready
    return d


def test_jump_is_single_edge_and_rearms_on_landing():
    d = calibrated_detector()
    assert d.update(pose(shoulder=.15, hip=.51), 2) == []
    assert d.update(pose(shoulder=.15, hip=.51), 2.06) == ['JUMP']
    assert d.update(pose(shoulder=.15, hip=.51), 2.2) == []
    for i in range(5):
        d.update(pose(), 2.5 + i * 0.1)
    assert d.update(pose(shoulder=.15, hip=.51), 4) == []
    assert d.update(pose(shoulder=.15, hip=.51), 4.06) == ['JUMP']


def test_duck_uses_persistence_and_off_hysteresis():
    d = calibrated_detector()
    assert d.update(pose(shoulder=.42, hip=.71, knee=110), 2) == []
    assert d.update(pose(shoulder=.43, hip=.72, knee=110), 2.2) == []
    assert d.update(pose(shoulder=.43, hip=.72, knee=110), 2.4) == ['DUCK_ON']
    d.update(pose(), 3)
    assert d.update(pose(), 3.22) == []
    assert d.update(pose(), 3.45) == []
    assert d.update(pose(), 3.7) == ['DUCK_OFF']


def test_does_not_detect_arm_only_or_weak_shoulder_raise():
    d = calibrated_detector()
    assert d.update(pose(shoulder=.20, hip=.60), 2) == []


def test_left_and_right_player_signals_are_independent():
    t = TwoPlayerTracker(calibration_frames=5)
    for i in range(5):
        assert t.process([pose(.2), pose(.8)], i / 30) == []
    assert t.ready
    assert t.process([pose(.2, shoulder=.15, hip=.51), pose(.8)], 2) == []
    assert t.process([pose(.2, shoulder=.15, hip=.51), pose(.8)], 2.06) == [('P1', 'JUMP')]
    assert t.process([pose(.2), pose(.8, shoulder=.15, hip=.51)], 3) == []
    assert t.process([pose(.2), pose(.8, shoulder=.15, hip=.51)], 3.06) == [('P2', 'JUMP')]


def test_missing_player_releases_duck_and_recalibrates_after_long_loss():
    t = TwoPlayerTracker(calibration_frames=5)
    for i in range(5):
        t.process([pose(.2), pose(.8)], i / 30)
    t.process([pose(.2, shoulder=.43, hip=.72, knee=110), pose(.8)], 2)
    t.process([pose(.2, shoulder=.43, hip=.72, knee=110), pose(.8)], 2.2)
    assert t.process([pose(.2, shoulder=.43, hip=.72, knee=110), pose(.8)], 2.4) == [('P1', 'DUCK_ON')]
    assert t.process([pose(.8)], 3.2) == [('P1', 'DUCK_OFF')]
    t.process([pose(.8)], 6)
    assert not t.detectors[0].ready
