import json
import logging
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def generate_json(system: str, user_text: str, schema: type[BaseModel]) -> dict:
    """Call Gemini and return schema-constrained JSON as a dict."""
    if not settings.gemini_api_key:
        raise AppError("AI is not configured", 503, "ai_not_configured")
    try:
        resp = _client().models.generate_content(
            model=settings.gemini_model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
            ),
        )
        return json.loads(resp.text)
    except Exception as e:
        logger.exception("Gemini call failed")
        detail = f" ({type(e).__name__}: {e})"[:300] if settings.app_env == "development" else ""
        raise AppError(f"AI service is unavailable. Please try again.{detail}", 502, "ai_error")
    
get_client = _client

def generate_text(system: str, user_text: str, temperature: float = 0.4) -> str:
    if not settings.gemini_api_key:
        raise AppError("AI is not configured", 503, "ai_not_configured")
    try:
        resp = _client().models.generate_content(
            model=settings.gemini_model,
            contents=user_text,
            config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
        )
        return (resp.text or "").strip()
    except Exception as e:
        logger.exception("Gemini text call failed")
        detail = f" ({type(e).__name__}: {e})"[:300] if settings.app_env == "development" else ""
        raise AppError(f"AI service is unavailable. Please try again.{detail}", 502, "ai_error")