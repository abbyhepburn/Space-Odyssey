"""Optional Gemini authoring. Validation and fallback remain application-owned."""
import os
from mission_catalog import Mission, fallback

async def generate(capabilities, index):
    local=fallback(capabilities,index)
    if not os.getenv('GEMINI_API_KEY'): return local,'Local mission catalog'
    try:
        from google import genai
        from google.genai import types
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=types.HttpOptions(timeout=12000)).aio as client:
            result=await client.models.generate_content(model=os.getenv('GEMINI_MODEL','gemini-2.5-flash'),
                contents=f'Create a short Saturn racing challenge. Capabilities: {capabilities}. Allowed: SATURN_SPRINT target 4-20 time 15-60; SATURN_JUMP and SATURN_DUCK target 1-5 time 20-90. Use only available abilities. Themes ice, amber, aurora.',
                config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=Mission))
            mission=Mission.model_validate_json(result.text).compatible('RACE',capabilities)
            return mission,'Gemini connected'
    except Exception:
        return local,'Gemini unavailable or invalid response — local fallback'
