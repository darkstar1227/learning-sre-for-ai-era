from prometheus_client import Counter


# 對應 Day8.md 段落 ⑦：低基數 label（quality_status/safety_status/risk_level/action_type），
# 不放 request_id、question、document_id 等高基數欄位。
ai_response_evaluations_total = Counter(
    "ai_response_evaluations_total",
    "AI /ask responses classified by quality and safety status",
    ["quality_status", "safety_status"],
)

ai_response_review_required_total = Counter(
    "ai_response_review_required_total",
    "AI /ask responses flagged for human review, by risk level",
    ["risk_level"],
)

ai_unsafe_action_blocked_total = Counter(
    "ai_unsafe_action_blocked_total",
    "Tool actions blocked by the safety authorization check",
    ["action_type"],
)
