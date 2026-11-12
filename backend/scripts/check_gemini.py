import sys

sys.path.insert(0, ".")

from google import genai
from google.genai import types

from app.ai.schemas import ParsedInvoiceLLM
from app.core.config import get_settings

s = get_settings()
print("model:", s.gemini_model, "| key set:", bool(s.gemini_api_key), "| key length:", len(s.gemini_api_key))
c = genai.Client(api_key=s.gemini_api_key)

print("\n1) Models available to your key:")
try:
    for m in c.models.list():
        if "generateContent" in (getattr(m, "supported_actions", None) or []):
            print("  ", m.name)
except Exception as e:
    print("  LIST FAILED:", type(e).__name__, e)

print("\n2) Plain call:")
try:
    print("  ", c.models.generate_content(model=s.gemini_model, contents="Say hi").text)
except Exception as e:
    print("  FAILED:", type(e).__name__, e)

print("\n3) Structured call:")
try:
    r = c.models.generate_content(
        model=s.gemini_model,
        contents="Invoice Rahul $20 for haircut, due in 5 days",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedInvoiceLLM,
            temperature=0.0,
        ),
    )
    print("  ", r.text)
except Exception as e:
    print("  FAILED:", type(e).__name__, e)