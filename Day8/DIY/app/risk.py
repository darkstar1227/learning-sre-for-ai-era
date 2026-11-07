from typing import Literal


HIGH_RISK_KEYWORDS = (
    "salary",
    "薪資",
    "醫療",
    "medical",
    "legal",
    "法律",
    "finance",
    "財務",
    "personal data",
    "個資",
    "resign",
    "離職",
    "fire",
    "解雇",
)


def classify_risk_level(question: str) -> Literal["low", "medium", "high"]:
    """對問題做最粗略的風險分級，只用來決定 Safety Check 3 是否該檢查得更嚴格。

    這不是語意分類器，只是關鍵字比對——跟 Day8.md 反覆強調的「規則只能抓明確情況」是同一件事。
    """
    lowered = question.lower()
    if any(keyword in lowered for keyword in HIGH_RISK_KEYWORDS):
        return "high"
    return "low"
