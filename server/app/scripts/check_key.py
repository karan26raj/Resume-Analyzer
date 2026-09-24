from google import genai

client = genai.Client(
    api_key="PASTE_YOUR_KEY_HERE"
)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello"
)

print(response.text)