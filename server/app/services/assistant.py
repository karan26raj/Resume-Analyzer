import time
from google import genai

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

for attempt in range(3):
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt
        )
        break

    except Exception as e:

        if "503" in str(e):
            time.sleep(5)
            continue

        raise

else:
    raise Exception(
        "Gemini service unavailable after 3 retries"
    )