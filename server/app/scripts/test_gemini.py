"""Manual smoke test for the Gemini connection: python -m app.scripts.test_gemini"""
from google.genai import types

from app.ai.gemini import generate_content_with_fallback

response, model_used = generate_content_with_fallback(
    contents="Hello",
    config=types.GenerateContentConfig(),
)

print(f"[{model_used}] {response.text}")
