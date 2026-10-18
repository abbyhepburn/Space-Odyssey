from collections import deque
import controller_check


class FakeUsb:
    def __init__(self,lines):self.lines=deque(lines)
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read_until(self,*args,**kwargs):return self.lines.popleft() if self.lines else b''


def run_check(monkeypatch,lines):
    now=[0.]
    def clock():now[0]+=.05;return now[0]
    monkeypatch.setattr(controller_check.time,'monotonic',clock)
    monkeypatch.setattr(controller_check.serial,'Serial',lambda *a,**kw:FakeUsb(lines))
    return controller_check.check('TEST-ONLY',seconds=2)


def test_bench_check_requires_motion_and_button_from_both_players(monkeypatch):
    lines=[f'REMOTE,P{p},{value}\n'.encode() for p in (1,2) for value in (
        'STATE,0.4,0.6,-0.5','MPU,1,0,0,9.81,0,0,0','SHAKE','SELECT')]
    result=run_check(monkeypatch,lines)
    assert result['passed']
    assert all(r['tilt_seen'] and r['shake_seen'] and r['button_seen'] and r['imu_ok'] for r in result['players'].values())


def test_bench_check_never_calls_a_missing_controller_a_pass(monkeypatch):
    result=run_check(monkeypatch,[b'REMOTE,P1,STATE,0,0,0\n',b'REMOTE,P1,MPU,1,nan,0,0,0,0,0\n'])
    assert not result['passed'] and result['invalid_lines']==1
    assert not result['players']['P1']['tilt_seen'] and not result['players']['P2']['states']
