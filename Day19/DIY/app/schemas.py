from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class GoldenDatasetEntry(BaseModel):
    """Schema for a single golden dataset entry.

    Represents a test case for AI evaluation covering:
    - task_success: does the task complete?
    - quality: is the output correct/relevant/usable?
    - safety: is the output acceptable?
    """

    id: str = Field(
        ...,
        description="Unique identifier for this test case"
    )

    input: str = Field(
        ...,
        description="The user query or request"
    )

    expected_status: Literal[
        "success",                      # Clear answer available
        "insufficient_context",         # No context to answer
        "high_risk_rejection_needed",   # Harmful/policy violation
        "invalid_tool_schema",          # Tool definition broken
    ] = Field(
        ...,
        description="Expected outcome category"
    )

    expected_output: Optional[str] = Field(
        default=None,
        description="For success cases: expected correct answer or keywords to find"
    )

    required_citations: Optional[list[str]] = Field(
        default=None,
        description="For quality cases: required sources that must be cited"
    )

    rejection_reason: Optional[str] = Field(
        default=None,
        description="For safety cases: why this should be rejected"
    )

    reviewed_by: str = Field(
        ...,
        description="Who reviewed and approved this test case"
    )

    reviewed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this case was reviewed"
    )

    recheck_at: Optional[datetime] = Field(
        default=None,
        description="When this case should be re-reviewed (e.g., if dataset drifts)"
    )

    notes: Optional[str] = Field(
        default=None,
        description="Additional context or explanation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "no-context",
                "input": "不存在的政策？",
                "expected_status": "insufficient_context",
                "reviewed_by": "reviewer@example.com",
                "reviewed_at": "2026-09-21T00:00:00",
                "notes": "Policy doesn't exist in knowledge base"
            }
        }
