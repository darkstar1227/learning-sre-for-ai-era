from dataclasses import dataclass
from uuid import uuid4

from google import genai

from app.config import get_settings
from app.prompt import build_prompt
from app.retrieval import retrieve_context


settings = get_settings()

client = genai.Client(
    api_key=settings.gemini_api_key,
)


@dataclass(frozen=True)
class RawAskResult:
    """Retriever → LLM → Response parser 這一段的原始輸出，evaluation.py 再做分類。"""

    request_id: str
    question: str
    answer: str
    sources: list[str]
    retrieved_document_ids: list[str]
    retrieval_count: int
    answer_status: str
    prompt_version: str


async def ask_grounded(
    question: str,
) -> RawAskResult:
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

    return RawAskResult(
        request_id=request_id,
        question=question,
        answer=answer,
        sources=[document.document_id for document in documents],
        retrieved_document_ids=[document.document_id for document in documents],
        retrieval_count=len(documents),
        answer_status=answer_status,
        prompt_version=settings.prompt_version,
    )
