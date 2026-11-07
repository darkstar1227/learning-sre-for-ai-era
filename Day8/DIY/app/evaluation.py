from app.llm import RawAskResult, ask_grounded
from app.logging_utils import log_evaluation
from app.metrics import (
    ai_response_evaluations_total,
    ai_response_review_required_total,
)
from app.quality_checks import (
    insufficient_context_handled,
    response_matches_contract,
    sources_are_allowed,
)
from app.risk import classify_risk_level
from app.safety_checks import is_high_risk_uncertainty, scan_sensitive_fields
from app.schemas import AskResponse, QualityStatus, SafetyStatus, TechnicalStatus


def _evaluate_quality(raw: RawAskResult) -> QualityStatus:
    payload = {
        "answer": raw.answer,
        "sources": raw.sources,
        "request_id": raw.request_id,
    }
    if not response_matches_contract(payload):
        return QualityStatus.INVALID_FORMAT

    if not sources_are_allowed(raw.sources, set(raw.retrieved_document_ids)):
        return QualityStatus.UNGROUNDED

    if raw.retrieval_count == 0:
        if insufficient_context_handled(raw.answer):
            return QualityStatus.PASS
        return QualityStatus.UNGROUNDED

    return QualityStatus.PASS


def _evaluate_safety(
    raw: RawAskResult,
    risk_level: str,
) -> tuple[SafetyStatus, str | None]:
    hits = scan_sensitive_fields(raw.answer)
    if hits:
        return SafetyStatus.BLOCKED, f"restricted_term_detected:{','.join(hits)}"

    if is_high_risk_uncertainty(
        risk_level=risk_level,
        retrieval_count=raw.retrieval_count,
        answer=raw.answer,
    ):
        return SafetyStatus.NEEDS_REVIEW, "high_risk_uncertainty"

    return SafetyStatus.PASS, None


async def evaluate_ask(question: str) -> AskResponse:
    """Day8.md 段落 ④ 的 pipeline：Retriever → LLM → Quality checks → Safety checks → Classification。"""
    raw = await ask_grounded(question)

    risk_level = classify_risk_level(question)
    quality_status = _evaluate_quality(raw)
    safety_status, block_reason = _evaluate_safety(raw, risk_level)

    requires_human_review = quality_status == QualityStatus.NEEDS_REVIEW or safety_status in (
        SafetyStatus.NEEDS_REVIEW,
        SafetyStatus.POLICY_VIOLATION,
    )

    ai_response_evaluations_total.labels(
        quality_status=quality_status.value,
        safety_status=safety_status.value,
    ).inc()

    if requires_human_review:
        ai_response_review_required_total.labels(risk_level=risk_level).inc()

    log_evaluation(
        request_id=raw.request_id,
        technical_status=TechnicalStatus.SUCCESS.value,
        workflow_status=TechnicalStatus.SUCCESS.value,
        quality_status=quality_status.value,
        safety_status=safety_status.value,
        retrieval_count=raw.retrieval_count,
        source_count=len(raw.sources),
        risk_level=risk_level,
        requires_human_review=requires_human_review,
        block_reason=block_reason,
    )

    answer = raw.answer
    if safety_status == SafetyStatus.BLOCKED:
        # Safety block 之後不把原始（可能含敏感內容的）答案吐回呼叫者。
        answer = "This response was withheld by a safety check. See audit log for detail."

    return AskResponse(
        answer=answer,
        sources=raw.sources,
        retrieved_document_ids=raw.retrieved_document_ids,
        retrieval_count=raw.retrieval_count,
        answer_status=raw.answer_status,
        prompt_version=raw.prompt_version,
        technical_status=TechnicalStatus.SUCCESS,
        workflow_status=TechnicalStatus.SUCCESS,
        quality_status=quality_status,
        safety_status=safety_status,
        risk_level=risk_level,
        requires_human_review=requires_human_review,
        request_id=raw.request_id,
    )
