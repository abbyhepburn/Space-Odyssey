from vision import Detector

def test_jump_rearm_and_duck_hysteresis():
    d=Detector()
    for i in range(45): assert not d.update(.5,.9,175,i/30)
    assert d.update(.42,.84,175,2)==['JUMP']
    assert d.update(.42,.84,175,3)==[]
    d.update(.5,.9,175,4)
    assert d.update(.42,.84,175,5)==['JUMP']
    d.update(.5,.9,175,6)
    assert d.update(.65,.9,110,7)==[]
    assert d.update(.65,.9,110,7.3)==['DUCK_ON']
    d.update(.5,.9,175,8)
    assert d.update(.5,.9,175,8.3)==['DUCK_OFF']
