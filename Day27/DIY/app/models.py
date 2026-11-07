"""
Data models for incident and postmortem documentation.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Incident severity levels."""
    SEV1 = "SEV1"  # Critical - all users affected
    SEV2 = "SEV2"  # Major - significant impact
    SEV3 = "SEV3"  # Minor - limited impact
    SEV4 = "SEV4"  # Informational - no user impact


class IncidentStage(str, Enum):
    """Stages of incident response."""
    DETECT = "detect"
    TRIAGE = "triage"
    MITIGATE = "mitigate"
    RECOVER = "recover"
    POSTMORTEM = "postmortem"


class AlertInfo(BaseModel):
    """Information about the alert that detected the incident."""
    name: str = Field(..., description="Alert name, e.g. 'P99 latency > 5s'")
    triggered_at: datetime = Field(..., description="When the alert triggered (UTC)")
    threshold: str = Field(..., description="Threshold that was violated")
    current_value: str = Field(..., description="Current value that triggered alert")


class TriageInfo(BaseModel):
    """Triage stage - initial assessment."""
    incident_commander: str = Field(..., description="Name of incident commander")
    severity: SeverityLevel = Field(..., description="Severity level")
    affected_systems: List[str] = Field(default_factory=list, description="Systems affected")
    estimated_impact_scope: str = Field(..., description="Estimated user/request impact")
    immediate_risk: str = Field(..., description="What's the immediate risk if not addressed?")


class MitigationStep(BaseModel):
    """A single mitigation action."""
    action: str = Field(..., description="Description of action taken")
    executed_at: datetime = Field(..., description="When action was executed (UTC)")
    expected_effect: str = Field(..., description="Expected improvement")
    actual_effect: str = Field(..., description="Actual observed improvement")


class RecoveryInfo(BaseModel):
    """Recovery stage - proof that issue is resolved."""
    recovery_completed_at: datetime = Field(..., description="When SLI returned to baseline")
    sli_metric: str = Field(..., description="SLI that was monitored, e.g. 'P99 latency'")
    baseline_value: str = Field(..., description="Normal baseline value")
    recovery_value: str = Field(..., description="Value at recovery time")
    verification_method: str = Field(..., description="How was recovery verified?")


class RootCauseAnalysis(BaseModel):
    """Root cause analysis for postmortem."""
    root_cause: str = Field(..., description="Technical root cause (system condition, not human error)")
    contributing_factors: List[str] = Field(default_factory=list, description="List of contributing factors")
    detection_gap: Optional[str] = Field(None, description="Why detection system missed this?")
    prevention_gap: Optional[str] = Field(None, description="What preventive measure was missing?")


class AISpecificFactors(BaseModel):
    """AI-specific factors for postmortem (when applicable)."""
    model_version: Optional[str] = Field(None, description="Model version at time of incident")
    prompt_version: Optional[str] = Field(None, description="Prompt template version")
    retrieval_index_version: Optional[str] = Field(None, description="RAG index version")
    embedding_model: Optional[str] = Field(None, description="Embedding model used")
    evaluation_coverage_gap: Optional[str] = Field(None, description="Why evaluation missed this?")
    safety_check_status: Optional[str] = Field(None, description="Did safety checks work? Where did they fail?")
    affected_input_types: Optional[str] = Field(None, description="Which input types triggered the issue?")


class ActionItem(BaseModel):
    """Post-incident action item."""
    title: str = Field(..., description="Action item title")
    owner: str = Field(..., description="Person responsible")
    deadline: Optional[datetime] = Field(None, description="Target completion date")
    category: str = Field(..., description="e.g. 'monitoring', 'runbook', 'testing', 'architecture'")
    priority: str = Field(..., description="high/medium/low")
    status: str = Field(default="open", description="open/in_progress/closed")


class Incident(BaseModel):
    """Complete incident documentation."""
    incident_id: str = Field(..., description="Unique incident identifier, e.g. INC-2026-001")
    title: str = Field(..., description="Brief incident title")
    severity: SeverityLevel = Field(..., description="Severity level")
    service_affected: str = Field(..., description="Primary service affected")
    created_at: datetime = Field(..., description="When incident was created")

    # Stage information
    detect: Optional[AlertInfo] = Field(None, description="Detection stage info")
    triage: Optional[TriageInfo] = Field(None, description="Triage stage info")
    mitigations: List[MitigationStep] = Field(default_factory=list, description="Mitigation actions taken")
    recovery: Optional[RecoveryInfo] = Field(None, description="Recovery stage info")

    # Post-incident analysis
    postmortem_completed_at: Optional[datetime] = Field(None, description="When postmortem was completed")
    root_cause: Optional[RootCauseAnalysis] = Field(None, description="Root cause analysis")
    ai_factors: Optional[AISpecificFactors] = Field(None, description="AI-specific factors (if applicable)")
    action_items: List[ActionItem] = Field(default_factory=list, description="Improvement action items")

    # Lessons learned
    what_went_well: List[str] = Field(default_factory=list, description="What defensive measures worked?")
    what_we_learned: List[str] = Field(default_factory=list, description="Key insights from this incident")


class RunbookEntry(BaseModel):
    """A single runbook entry for a known issue."""
    issue_name: str = Field(..., description="Issue name, e.g. 'Database connection pool exhaustion'")
    symptoms: List[str] = Field(..., description="Observable symptoms")
    diagnosis_steps: List[str] = Field(..., description="Steps to diagnose")
    mitigation_strategies: List[str] = Field(..., description="Ways to mitigate")
    escalation_criteria: Optional[str] = Field(None, description="When to escalate?")
    reference_incidents: List[str] = Field(default_factory=list, description="Related incident IDs")
