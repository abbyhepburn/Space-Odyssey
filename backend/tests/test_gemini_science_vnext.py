"""Regression tests: generated science/arcade missions are playable and safe."""
import asyncio
import json
import sys
import types

from flight_game import (
    FlightGame, SCIENCE_MODES, ACTION_MODES, MOVES, eligible_gemini_modes,
    generate_game, local_mission,
)


def advance(game, seconds):
    for _ in range(round(seconds * 20)):
        game.tick(.05)


def test_gemini_selects_actual_game_family_not_just_a_name(monkeypatch):
    """A fake SDK response demonstrates the real structured integration, no API calls."""
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')
    calls = []

    class FakeResult:
        text = json.dumps({
            'game_type': 'SCIENCE_QUIZ',
            'name': 'Jupiter Research Showdown',
            'briefing': 'Pick the correct facts about Jupiter before your rival does.',
            'event_pattern': 'ALTERNATING',
        })

    class FakeModels:
        async def generate_content(self, **kwargs):
            calls.append(kwargs)
            return FakeResult()

    class FakeAio:
        models = FakeModels()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs['api_key'] == 'fake-test-key'
            self.aio = FakeAio()

    fake_types = types.ModuleType('google.genai.types')
    fake_types.HttpOptions = lambda **kw: kw
    fake_types.GenerateContentConfig = lambda **kw: kw
    fake_genai = types.ModuleType('google.genai')
    fake_genai.Client = FakeClient
    fake_genai.types = fake_types
    fake_google = types.ModuleType('google')
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules, 'google', fake_google)
    monkeypatch.setitem(sys.modules, 'google.genai', fake_genai)
    monkeypatch.setitem(sys.modules, 'google.genai.types', fake_types)

    mission, source = asyncio.run(generate_game('JUPITER'))
    assert source == 'GEMINI · LIVE CHALLENGE'
    assert mission.game_type == 'SCIENCE_QUIZ'
    assert mission.name == 'Jupiter Research Showdown'
    assert mission.event_pattern == 'ALTERNATING'
    assert [m.control for m in mission.movements] == ['TILT', 'PRESS']
    assert mission.time_limit_s == 15 and mission.obstacle_count == 5
    assert not mission.sync_boost
    assert calls and 'SCIENCE_QUIZ' in calls[0]['contents']
    assert 'response_json_schema' in calls[0]['config']


def test_ineligible_ai_game_is_rejected_and_uses_valid_fallback(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-test-key')

    class FakeModels:
        async def generate_content(self, **kwargs):
            return types.SimpleNamespace(text=json.dumps({
                'game_type': 'SAMPLE_HUNT', 'name': 'Impossible Jupiter Landing',
                'briefing': 'This game would place players on Jupiter’s surface.',
                'event_pattern': 'SCATTERED'
            }))

    class FakeAio:
        models = FakeModels()
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False

    class FakeClient:
        def __init__(self, **kwargs): self.aio = FakeAio()

    fake_types = types.SimpleNamespace(HttpOptions=lambda **kw: kw,
                                       GenerateContentConfig=lambda **kw: kw)
    fake_genai = types.SimpleNamespace(Client=FakeClient, types=fake_types)
    fake_google = types.ModuleType('google')
    fake_google.genai = fake_genai
    monkeypatch.setitem(sys.modules,'google',fake_google)
    monkeypatch.setitem(sys.modules,'google.genai',fake_genai)
    monkeypatch.setitem(sys.modules,'google.genai.types',fake_types)

    mission, source = asyncio.run(generate_game('JUPITER'))
    assert source == 'LOCAL · GEMINI RESPONSE REJECTED'
    assert mission.game_type != 'SAMPLE_HUNT'
    mission.validate_planet('JUPITER')


def test_science_and_arcade_categories_alternate_even_offline(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)

    async def scenario():
        played = []
        for _ in range(8):
            mission, source = await generate_game('MARS', global_recent=played)
            assert source == 'LOCAL · NO API KEY'
            assert mission.game_type in MOVES
            assert (mission.game_type in SCIENCE_MODES) == (len(played) % 2 == 0)
            played.append(mission.game_type)
    asyncio.run(scenario())


def test_remote_left_right_changes_quiz_answer_for_both_players():
    game=FlightGame(simulated=False)
    game.planet='SATURN'
    game.mission=local_mission('SATURN','SCIENCE_QUIZ')
    game.start_mission()
    # Hardware packet's second analog value is the joystick/tilt horizontal,
    # not the navigation throttle; mission mode remaps it to answer selection.
    game.command('FLIGHT,P1,AXIS,0,-1',source='remote')
    game.command('FLIGHT,P2,AXIS,0,1',source='remote')
    advance(game,.55)
    # Refresh the physical signal after the 400-ms disconnect safety timeout.
    game.command('FLIGHT,P1,AXIS,0,-1',source='remote')
    game.command('FLIGHT,P2,AXIS,0,1',source='remote')
    game.tick(.05)
    assert game.players[0]['selection'] == 0
    assert game.players[1]['selection'] == 2
    assert game.snapshot()['quiz'] is not None
    quiz=game.obstacles[0]
    # Correct answer is always sourced from the local verified catalogue.
    wanted=quiz['answer']
    game.command(f'FLIGHT,P1,AXIS,0,{(wanted-1)}',source='remote')
    game.tick(.05)
    game.command('FLIGHT,P1,SELECT',source='remote')
    assert game.players[0]['score']==25
    assert quiz['passed'][0] is True
    # Duplicate press cannot award points again.
    game.command('FLIGHT,P1,SELECT',source='remote')
    assert game.players[0]['score']==25
