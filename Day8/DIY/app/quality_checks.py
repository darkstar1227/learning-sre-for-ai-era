"""Deterministic Quality checks for Day8.md 段落 ⑤.

These checks only catch what can be turned into an explicit rule. They cannot
prove an answer is actually correct — see Day8.md ①/④ for that boundary.
"""

INSUFFICIENT_CONTEXT_MARKERS = (
    "no information",
    "not available",
    "cannot confirm",
    "does not contain",
    "unavailable",
    "no data",
    "無法確認",
    "沒有足夠資訊",
    "無法根據",
    "資料不足",
    "沒有這項資訊",
)


def response_matches_contract(payload: dict) -> bool:
    """Check 1：回答格式是否符合 API contract？"""
    answer = payload.get("answer")
    sources = payload.get("sources")
    request_id = payload.get("request_id")

    if not isinstance(answer, str) or not answer.strip():
        return False
    if not isinstance(sources, list):
        return False
    if not isinstance(request_id, str) or not request_id:
        return False
    return True


def sources_are_allowed(
    answer_sources: list[str],
    retrieved_ids: set[str],
) -> bool:
    """Check 2：引用是否真的來自 Retriever 結果？"""
    return set(answer_sources).issubset(retrieved_ids)


def insufficient_context_handled(answer: str) -> bool:
    """Check 3：沒有 context 時，有沒有誠實處理？"""
    lowered = answer.lower()
    return any(marker in lowered for marker in INSUFFICIENT_CONTEXT_MARKERS)


def expected_facts_present(
    answer: str,
    expected_facts: list[str],
) -> bool:
    """Check 4：關鍵事實是否存在？（僅適用於 golden dataset，非 production 逐筆檢查）"""
    lowered = answer.lower()
    return all(fact.lower() in lowered for fact in expected_facts)
