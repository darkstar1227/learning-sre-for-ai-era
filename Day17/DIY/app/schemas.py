"""Data schemas for requests, responses, and events."""

from typing import Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request schema for /ask endpoint."""

    question: str = Field(..., min_length=1, description="User question")


class AskResponse(BaseModel):
    """Response schema for /ask endpoint."""

    answer: str = Field(..., description="LLM response")


class DependencyOutcome(BaseModel):
    """Outcome of a dependency call."""

    provider: str = Field(..., description="Dependency provider name (e.g., 'llm_provider')")
    status: str = Field(..., description="Outcome status: 'success', 'timeout', 'error'")
    latency_ms: int = Field(..., description="Latency in milliseconds")


class SLIEvent(BaseModel):
    """Minimal event format for SLI tracking.

    This follows the format from Day 17 article:
    - No sensitive data (prompt, user_id, complete_answer) in labels
    - Low-cardinality fields only
    - Dependency outcome tracked separately
    """

    route: str = Field(..., description="API route (e.g., '/ask')")
    status: str = Field(
        ...,
        description="Request outcome: 'good' | 'timeout' | 'malformed' | 'error'",
    )
    latency_ms: int = Field(..., description="Request completion time in milliseconds")
    dependency: Optional[str] = Field(
        None, description="Primary dependency name (e.g., 'llm_provider')"
    )
    dependency_outcome: Optional[DependencyOutcome] = Field(
        None, description="Dependency call details"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "route": "/ask",
                "status": "good",
                "latency_ms": 1200,
                "dependency": "llm_provider",
                "dependency_outcome": {
                    "provider": "llm_provider",
                    "status": "success",
                    "latency_ms": 1100,
                },
            }
        }
