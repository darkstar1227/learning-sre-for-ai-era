from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    retrieved_document_ids: list[str]
    retrieval_count: int
    answer_status: Literal["answered", "unavailable"]
    prompt_version: str
    technical_success: bool
    semantic_risk: Literal["unknown"] = "unknown"
    request_id: str
