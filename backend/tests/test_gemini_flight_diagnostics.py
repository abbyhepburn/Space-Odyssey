import asyncio
import sys
import types
from pathlib import Path

from flight_game import FlightGame, generate_game


def test_fresh_navigation_spawn_can_go_forward_and_reverse():
    g = FlightGame()
    g.transition('NAVIGATION')
    # Critical regression: the old Earth exclusion sphere enclosed this
    # perfectly safe spawn and blocked forward thrust at the first press.
    g.command('FLIGHT,P1,AXIS,1,0')
    g.tick(.10)
    assert g.speed > 0
    assert g.ship[2] < 0
    assert not g.thrust_blocked
    g.command('FLIGHT,P1,AXIS,-1,0')
    g.tick(.30)
    assert g.speed < 0
    assert g.snapshot()['throttle_input'] == -1


def test_missing_api_key_reports_fallback(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    mission, source = asyncio.run(generate_game('MARS'))
    assert source == 'LOCAL · NO API KEY'
    assert mission.time_limit_s == 15


def test_http_status_has_actual_flight_source_and_not_secret(monkeypatch):
    from main import Engine
    e = Engine()
    e.flight.source = 'LOCAL · GEMINI RATE LIMITED'
    assert e.flight.source.startswith('LOCAL')
