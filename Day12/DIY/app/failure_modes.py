"""AI workflow failure-mode matrix.

This module defines the failure-mode matrix from Day 12, mapping each workflow
node's potential failures to:
- Observable symptoms
- Machine-readable status codes
- Evidence trail that can be collected
- Safe/defensive action path
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FailureMode:
    """A single failure scenario in the workflow."""

    node: str
    failure_description: str
    external_status: str
    evidence_field: str
    evidence_collection: str
    safe_action: str


FAILURE_MODE_MATRIX = [
    FailureMode(
        node="retrieve",
        failure_description="沒有足夠 context，但模型用一般知識補滿答案",
        external_status="insufficient_context",
        evidence_field="trace 的文件數與版本",
        evidence_collection="retrieval_doc_count, retrieval_version in trace/response",
        safe_action="不生成具體結論，return null answer with status=insufficient_context",
    ),
    FailureMode(
        node="retrieve",
        failure_description="文件更新後 embedding 尚未重建，回答引用舊政策",
        external_status="stale_index",
        evidence_field="embedding index version mismatch",
        evidence_collection="retrieval_version tag in trace vs expected current version",
        safe_action="log version mismatch, escalate to human review for re-indexing",
    ),
    FailureMode(
        node="prompt_build",
        failure_description="context 過長觸發 token 限制，prompt 被截斷",
        external_status="context_truncated",
        evidence_field="prompt token count vs model limit",
        evidence_collection="token_count field in trace, actual prompt in debug logs",
        safe_action="return insufficient_context status instead of truncating silently",
    ),
    FailureMode(
        node="model_output",
        failure_description="LLM 調用超時，沒有生成完整回覆",
        external_status="llm_timeout",
        evidence_field="請求耗時 vs timeout 閾值",
        evidence_collection="duration_ms in trace, timeout_ms in config",
        safe_action="catch timeout exception, return structured error without guessing",
    ),
    FailureMode(
        node="model_output",
        failure_description="模型或 prompt 版本改動，同一 evaluation case 品質下降",
        external_status="regression_detected",
        evidence_field="模型版本/commit hash 與上次執行不同",
        evidence_collection="model_name, model_version in response; regression test suite",
        safe_action="flag for evaluation queue, don't auto-promote to production",
    ),
    FailureMode(
        node="tool_call",
        failure_description="model 產生 JSON 但欄位型別不符 tool contract",
        external_status="tool_validation_failed",
        evidence_field="schema validation error details",
        evidence_collection="validation_error in response/trace",
        safe_action="不執行 action，return error status with schema_errors list",
    ),
    FailureMode(
        node="tool_call",
        failure_description="agent 重試 tool action，造成重複寫入",
        external_status="duplicate_write_risk",
        evidence_field="idempotency key and invocation count",
        evidence_collection="idempotency_key field, retry_count in trace",
        safe_action="enforce idempotency key on all write actions, fail on duplicate",
    ),
    FailureMode(
        node="tool_call",
        failure_description="模型缺乏權限執行請求的 action",
        external_status="tool_permission_denied",
        evidence_field="權限檢查結果和 caller identity",
        evidence_collection="permission_granted field, caller_id in audit trail",
        safe_action="return permission_denied status, require explicit approval for escalation",
    ),
    FailureMode(
        node="response",
        failure_description="citation 引用的內容實際不存在於檢索結果中（幻覺）",
        external_status="quality_failed",
        evidence_field="request_id、trace_id、retrieved docs 清單",
        evidence_collection="citations vs retrieval_result docs comparison",
        safe_action="send to evaluation queue with citation_mismatch flag, don't return to user",
    ),
    FailureMode(
        node="agent_loop",
        failure_description="agent 陷入重試迴圈達到上限，任務失敗",
        external_status="agent_loop_limit",
        evidence_field="重試次數和最後一步錯誤",
        evidence_collection="retry_count, max_retries, final_error in trace",
        safe_action="break loop, return error status and collected evidence for debugging",
    ),
]


def get_failure_mode_matrix_dict() -> list[dict]:
    """Return failure matrix as list of dicts for JSON serialization."""
    return [
        {
            "node": fm.node,
            "failure_description": fm.failure_description,
            "external_status": fm.external_status,
            "evidence_field": fm.evidence_field,
            "evidence_collection": fm.evidence_collection,
            "safe_action": fm.safe_action,
        }
        for fm in FAILURE_MODE_MATRIX
    ]


def get_failure_modes_by_node(node: str) -> list[FailureMode]:
    """Get all failure modes for a specific workflow node."""
    return [fm for fm in FAILURE_MODE_MATRIX if fm.node == node]


def get_unique_nodes() -> list[str]:
    """Get list of all unique nodes in the matrix."""
    return sorted(set(fm.node for fm in FAILURE_MODE_MATRIX))
