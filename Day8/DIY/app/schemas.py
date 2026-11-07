from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TechnicalStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class QualityStatus(StrEnum):
    PASS = "pass"
    UNGROUNDED = "ungrounded"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    INVALID_FORMAT = "invalid_format"
    NEEDS_REVIEW = "needs_review"


class SafetyStatus(StrEnum):
    PASS = "pass"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"
    POLICY_VIOLATION = "policy_violation"


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
    technical_status: TechnicalStatus
    workflow_status: TechnicalStatus
    quality_status: QualityStatus
    safety_status: SafetyStatus
    risk_level: Literal["low", "medium", "high"]
    requires_human_review: bool
    request_id: str
