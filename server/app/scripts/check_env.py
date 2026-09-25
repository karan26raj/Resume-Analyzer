from app.core.config import settings


def _mask(secret: str | None) -> str:
    if not secret:
        return "<not set>"
    return f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "****"


print("GEMINI_API_KEY:", _mask(settings.GEMINI_API_KEY))
print("GEMINI_MODEL:", settings.GEMINI_MODEL)
