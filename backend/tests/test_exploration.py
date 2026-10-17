import asyncio
import pytest
from exploration import Exploration, PlanetMission, Objective, fallback, create_mission, PLANETS, CONTROLS

def test_fallback_all_planets_and_available_controls():
    for planet in PLANETS:
        for controls in [CONTROLS,('JUMP',),('DUCK',),('SHAKE',)]:
            assert fallback(planet,controls).validate_context(planet,controls)
    with pytest.raises(ValueError): fallback('SATURN',())

def test_wrong_context_rejected():
    m=fallback('SATURN',CONTROLS)
    with pytest.raises(ValueError): m.validate_context('MARS',CONTROLS)
    with pytest.raises(ValueError): m.validate_context('SATURN',('JUMP',))

def test_no_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    m,source=asyncio.run(create_mission('MARS',CONTROLS))
    assert m.planet=='MARS' and 'FALLBACK' in source

def test_cooperation_window(monkeypatch):
    now=[100.];monkeypatch.setattr('exploration.time.monotonic',lambda:now[0])
    e=Exploration();e.mission=PlanetMission(planet='SATURN',title='Large asteroid',briefing='Clear the large asteroid together.',objectives=[Objective(action='COOP_SHAKE',instruction='Shake together.',target=1)],time_limit_s=60)
    e.progress=[0];e.outcome='READY';e.command('MISSION_START')
    e.action('P1','SHAKE');now[0]+=1.5;e.action('P2','SHAKE');assert e.progress==[0]
    now[0]+=.5;e.action('P1','SHAKE');assert e.outcome=='COMPLETE'

def test_expiry_reset_hardware(monkeypatch):
    now=[100.];monkeypatch.setattr('exploration.time.monotonic',lambda:now[0])
    e=Exploration();e.mission=fallback('SATURN',CONTROLS);e.progress=[0,0,0];e.outcome='READY';e.command('MISSION_START')
    now[0]+=121;e.action('P1','SHAKE');assert e.outcome=='EXPIRED' and e.progress==[0,0,0]
    e.command('PLANET,MARS');assert e.mission is None and e.planet=='MARS'
    with pytest.raises(ValueError):Exploration(False).action('P1','SHAKE')

def test_duck_release(monkeypatch):
    now=[100.];monkeypatch.setattr('exploration.time.monotonic',lambda:now[0])
    e=Exploration();e.mission=fallback('SATURN',('DUCK',));e.progress=[0];e.outcome='READY';e.command('MISSION_START')
    e.action('P1','DUCK');now[0]+=1;e.action('P1','DUCK');assert e.progress==[1]
    e.action('P1','DUCK_OFF');now[0]+=1;e.action('P1','DUCK');assert e.progress==[2]
