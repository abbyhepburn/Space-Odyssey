"""Run: python diagnose_gemini.py (inside backend with its venv activated).

Performs one actual Gemini challenge request using backend/.env.
The key is never printed or written to disk; this can incur API usage.
"""
import asyncio
import importlib.util
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(os.getenv('SPACE_ODYSSEY_ENV', str(Path(__file__).with_name('.env'))))


async def main():
    configured=bool(os.getenv('GEMINI_API_KEY', '').strip())
    try:
        installed=importlib.util.find_spec('google.genai') is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        installed=False
    model=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
    print('API key configured:', 'YES' if configured else 'NO')
    print('google-genai SDK installed:', 'YES' if installed else 'NO')
    print('Requested model:',model)
    if not configured:
        print('Add GEMINI_API_KEY to backend/.env (not the frontend).')
        return
    if not installed:
        print('Install the SDK in your active backend environment: python -m pip install google-genai')
        return
    from flight_game import generate_game
    mission,status=await generate_game('MARS', global_recent=['ASTEROID_DODGE'])
    print('Generation result:',status)
    print('Generated challenge:',mission.name)
    print('Game family:',mission.game_type)
    if not status.startswith('GEMINI'):
        print('The game used LOCAL FALLBACK. Check the category above; it is not live AI.')


if __name__=='__main__':
    asyncio.run(main())
