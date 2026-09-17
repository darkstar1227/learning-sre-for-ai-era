from google import genai

from app.config import get_settings


settings = get_settings()

client = genai.Client(
    api_key=settings.gemini_api_key,
)

interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Reply with exactly: Gemini connection OK",
)

print(interaction.output_text)
