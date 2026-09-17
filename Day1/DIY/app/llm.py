from google import genai
from langsmith import traceable, wrappers

from app.config import get_settings


settings = get_settings()

gemini_client = genai.Client(
    api_key=settings.gemini_api_key,
)

client = wrappers.wrap_gemini(
    gemini_client,
    tracing_extra={
        "tags": [
            "day01",
            "gemini",
        ],
        "metadata": {
            "provider": "google",
            "sdk": "google-genai",
        },
    },
)


SYSTEM_PROMPT = """
You are a concise SRE tutor.

Answer the user's question accurately and briefly.

If you are unsure, clearly state what is uncertain
instead of inventing information.
"""


@traceable(
    name="build_prompt",
    run_type="chain",
)
def build_prompt(
    question: str,
) -> str:

    return f"""
{SYSTEM_PROMPT}

User question:
{question}
""".strip()


@traceable(
    name="ask_workflow",
    run_type="chain",
)
async def ask_llm(
    question: str,
) -> dict[str, str]:

    prompt = build_prompt(question)

    interaction = await client.aio.interactions.create(
        model=settings.model_name,
        input=prompt,
    )

    return {
        "answer": interaction.output_text or "",
        "model": settings.model_name,
    }
