import asyncio
import pytest
from mission_catalog import Mission,fallback
from gemini_missions import generate

def test_capabilities_and_phase():
    m=fallback({'jump':True},1)
    with pytest.raises(ValueError): m.compatible('RACE',{'jump':False})
    for phase in ['CUTSCENE','COUNTDOWN','RESULTS']:
        with pytest.raises(ValueError): m.compatible(phase,{'jump':True})
    assert m.compatible('RACE',{'jump':True}) is m

def test_catalog_bounds():
    for index in range(6):
        caps={'jump':True,'duck':True}
        assert fallback(caps,index).compatible('RACE',caps)
    m=fallback({}); m.target=100
    with pytest.raises(ValueError): m.compatible('RACE',{})
    with pytest.raises(ValueError): Mission(mission_id='MARS',title='x',story='x',target=4,time_limit_s=20)

def test_no_key_fallback(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    m,status=asyncio.run(generate({},0))
    assert m.mission_id=='SATURN_SPRINT' and 'Local' in status
