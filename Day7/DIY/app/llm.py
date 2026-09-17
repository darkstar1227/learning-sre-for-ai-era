from uuid import uuid4

from google import genai

from app.config import get_settings
from app.prompt import build_prompt
from app.retrieval import retrieve_context
from app.schemas import AskResponse


settings = get_settings()

client = genai.Client(
    api_key=settings.gemini_api_key,
)


async def ask_grounded(
    question: str,
) -> AskResponse:
    request_id = f"req_{uuid4().hex[:12]}"

    documents = retrieve_context(question)

    prompt = build_prompt(
        question,
        documents,
    )

    answer_status = "answered" if documents else "unavailable"

    interaction = await client.aio.models.generate_content(
        model=settings.model_name,
        contents=prompt,
    )

    answer = interaction.text or ""

    return AskResponse(
        answer=answer,
        sources=[document.document_id for document in documents],
        retrieved_document_ids=[document.document_id for document in documents],
        retrieval_count=len(documents),
        answer_status=answer_status,
        prompt_version=settings.prompt_version,
        technical_success=True,
        semantic_risk="unknown",
        request_id=request_id,
    )
