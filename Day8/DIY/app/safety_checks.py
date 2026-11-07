"""Deterministic Safety checks for Day8.md 段落 ⑥.

Keyword matching cannot prove a response is safe; it only catches the
explicit, known-bad patterns this Lab decided to block. Real systems need
more than this — see Day8.md ⑥ for the same caveat.
"""

from typing import Literal


RESTRICTED_TERMS = (
    "password",
    "api key",
    "access token",
    "salary",
    "home address",
    "phone number",
    "national id",
    "身分證",
    "薪資",
    "家庭地址",
    "銀行帳號",
)

ToolPolicy = Literal["allowed", "requires_confirmation", "denied"]

# Day8/Detailed-outline.md 的工具清單：模型只能「提出」動作，
# 是否真的執行由這張表決定，跟模型自己怎麼講無關。
TOOL_ALLOWLIST: dict[str, ToolPolicy] = {
    "read_policy": "allowed",
    "search_documents": "allowed",
    "create_leave_request": "requires_confirmation",
    "send_email": "requires_confirmation",
    "delete_record": "denied",
}

CONFIDENT_MARKERS = (
    "definitely",
    "certainly",
    "guaranteed",
    "一定",
    "保證",
    "絕對",
    "100%",
)


def scan_sensitive_fields(text: str) -> list[str]:
    """Safety Check 1：敏感欄位遮罩——回傳命中的受限字詞，空 list 代表乾淨。"""
    lowered = text.lower()
    return [term for term in RESTRICTED_TERMS if term.lower() in lowered]


def authorize_tool_action(action_name: str) -> ToolPolicy:
    """Safety Check 2：未授權 Tool Action——不在名單內一律視為 denied（fail closed）。"""
    return TOOL_ALLOWLIST.get(action_name, "denied")


def is_high_risk_uncertainty(
    risk_level: Literal["low", "medium", "high"],
    retrieval_count: int,
    answer: str,
) -> bool:
    """Safety Check 3：高風險不確定性——context 不足卻講得斬釘截鐵，且題目屬中高風險。"""
    if risk_level not in ("medium", "high"):
        return False
    if retrieval_count > 0:
        return False

    lowered = answer.lower()
    return any(marker in lowered for marker in CONFIDENT_MARKERS)
