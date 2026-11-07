"""
Pydantic schemas for AI Change Management manifests.
Inspired by Day28: CI/CD & AI Change Management
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ChangeManifest(BaseModel):
    """
    AI Change Manifest: tracks all non-code artifacts in a deployment.

    Corresponds to Day28.md section ③ (寫 change manifest).
    """

    # Core identifiers
    change_id: str = Field(
        description="Unique identifier for this change (e.g., 'answer-v17')"
    )

    # AI artifact versions (from Day28.md section ②)
    code_revision: Optional[str] = Field(
        default=None,
        description="Git commit hash or tag (e.g., 'abc123def456')"
    )
    prompt_version: str = Field(
        description="Prompt identifier or timestamp (e.g., '2026-09-21-a')"
    )
    model: str = Field(
        description="Model identifier in 'provider/model-name' format (e.g., 'google/gemini-3.6-flash')"
    )
    golden_dataset: str = Field(
        description="Version of the evaluation dataset (e.g., 'v3')"
    )
    retrieval_index_version: Optional[str] = Field(
        default=None,
        description="Version of retrieval/vector index if applicable"
    )
    tool_schema_version: Optional[str] = Field(
        default=None,
        description="Version of tool schema definitions if applicable"
    )
    evaluator_version: Optional[str] = Field(
        default=None,
        description="Version of evaluation logic/rules if applicable"
    )

    # Release gate (from Day28.md section ①)
    release_gate: str = Field(
        description="Gate condition for release (e.g., 'citation_valid_and_safety_checks')"
    )

    # Rollback information (from Day28.md section ②)
    rollback: Optional[str] = Field(
        default=None,
        description="Previous change_id for quick rollback reference (e.g., 'answer-v16')"
    )

    # Ownership and timeline
    owner: str = Field(
        description="Team or person responsible for this change"
    )
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this manifest was created"
    )

    # Optional: planned observation metrics
    observation_metrics: Optional[List[str]] = Field(
        default=None,
        description="SLI, evaluation cases, or risk signals to watch (e.g., ['citation_accuracy', 'safety_blocks'])"
    )

    # Optional: compatibility notes for rollback
    compatibility_notes: Optional[str] = Field(
        default=None,
        description="Rollback compatibility considerations (e.g., 'new tool schema requires handler update')"
    )

    @field_validator("change_id", "model")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Ensure IDs and model names are non-empty."""
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        """Model should follow 'provider/name' or be 'TODO'."""
        v = v.strip()
        if v != "TODO" and "/" not in v:
            raise ValueError("model must be in 'provider/model-name' format or 'TODO'")
        return v

    def to_dict_for_manifest(self) -> dict:
        """Convert to dict for YAML serialization, removing None values."""
        data = self.model_dump(exclude_none=True)
        # Convert datetime to ISO string for YAML
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        return data


class PromptChange(BaseModel):
    """
    Expected observation scenario for a prompt change.
    Used to document what to watch for after deployment.
    """

    prompt_version: str
    expected_improvements: List[str] = Field(
        description="Expected positive behaviors after this prompt change"
    )
    risk_signals: List[str] = Field(
        description="Warning signals that would indicate rollback is needed"
    )
    evaluation_metrics: List[str] = Field(
        description="Specific SLI/quality metrics to monitor"
    )


class ModelChange(BaseModel):
    """
    Expected observation scenario for a model version change.
    Used to document what to watch for after deployment.
    """

    model_identifier: str
    expected_improvements: List[str] = Field(
        description="Expected positive behaviors from this model version"
    )
    risk_signals: List[str] = Field(
        description="Warning signals that would indicate rollback is needed"
    )
    cost_implications: Optional[str] = Field(
        default=None,
        description="Cost changes compared to previous model (e.g., '+15% per request')"
    )
    evaluation_metrics: List[str] = Field(
        description="Specific SLI/quality metrics to monitor"
    )
