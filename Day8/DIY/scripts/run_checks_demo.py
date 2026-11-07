"""不需要網路或真實 API Key 的驗證：直接對 quality_checks / safety_checks 的
deterministic 規則餵合成輸入，確認 Day8.md ⑤⑥ 描述的邏輯本身正確。

golden dataset（run_golden.py）驗證的是「整條 pipeline 接得起來」；
這支腳本驗證的是「規則本身有沒有寫對」，兩者互補，且都不需要真實 LLM 回答。
"""

from app.quality_checks import (
    expected_facts_present,
    insufficient_context_handled,
    response_matches_contract,
    sources_are_allowed,
)
from app.safety_checks import (
    authorize_tool_action,
    is_high_risk_uncertainty,
    scan_sensitive_fields,
)


FAILURES: list[str] = []


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main() -> None:
    # --- Quality Check 1：contract validation ---
    check(
        "Q1: 有效 payload 通過 contract",
        response_matches_contract(
            {"answer": "兩天", "sources": ["company-policy-remote-work"], "request_id": "req_1"}
        ),
    )
    check(
        "Q1: 缺少 answer 應該被拒絕",
        not response_matches_contract({"sources": [], "request_id": "req_1"}),
    )
    check(
        "Q1: sources 型別錯誤（非 list）應該被拒絕",
        not response_matches_contract(
            {"answer": "兩天", "sources": "company-policy-remote-work", "request_id": "req_1"}
        ),
    )

    # --- Quality Check 2：source grounding ---
    check(
        "Q2: 只引用有取回的來源視為通過",
        sources_are_allowed(
            ["company-policy-remote-work"],
            {"company-policy-remote-work"},
        ),
    )
    check(
        "Q2: 引用未取回的來源應被判定為 ungrounded",
        not sources_are_allowed(
            ["company-policy-remote-work", "employee-handbook-2025"],
            {"company-policy-remote-work"},
        ),
    )

    # --- Quality Check 3：insufficient context handling ---
    check(
        "Q3: 誠實說明資料不足應被辨識為已處理",
        insufficient_context_handled("目前文件沒有這項資訊，無法確認補助金額。"),
    )
    check(
        "Q3: 編造答案不應被誤判為已誠實處理",
        not insufficient_context_handled("公司每月會提供 1000 元網路補助。"),
    )

    # --- Quality Check 4：expected facts（golden dataset 用）---
    check(
        "Q4: 關鍵事實齊全時視為通過",
        expected_facts_present(
            "Full-time employees may work remotely up to two days, with manager approval.",
            ["two", "manager approval"],
        ),
    )
    check(
        "Q4: 缺少關鍵事實時應被抓出",
        not expected_facts_present(
            "Employees can work remotely.",
            ["two", "manager approval"],
        ),
    )

    # --- Safety Check 1：sensitive field masking ---
    hits = scan_sensitive_fields("這是他的 home address 與 salary 資訊。")
    check(f"S1: 命中受限字詞 {hits}", len(hits) > 0)
    check(
        "S1: 正常政策回答不誤觸敏感字詞",
        len(scan_sensitive_fields("Full-time employees may work remotely up to two days per week.")) == 0,
    )

    # --- Safety Check 2：tool authorization（fail closed）---
    check("S2: read_policy 應允許", authorize_tool_action("read_policy") == "allowed")
    check(
        "S2: send_email 應要求人工確認",
        authorize_tool_action("send_email") == "requires_confirmation",
    )
    check("S2: delete_record 應被拒絕", authorize_tool_action("delete_record") == "denied")
    check(
        "S2: 不在名單內的 action 預設拒絕（fail closed，而非 fail open）",
        authorize_tool_action("wire_transfer") == "denied",
    )

    # --- Safety Check 3：high-risk uncertainty ---
    check(
        "S3: 中高風險 + 無 context + 過度自信 → 需要人工 review",
        is_high_risk_uncertainty(risk_level="high", retrieval_count=0, answer="這一定是對的，保證沒問題。"),
    )
    check(
        "S3: 低風險問題即使講得肯定也不觸發",
        not is_high_risk_uncertainty(risk_level="low", retrieval_count=0, answer="這一定是對的。"),
    )
    check(
        "S3: 已有 context 支持時不算「不確定性」問題",
        not is_high_risk_uncertainty(risk_level="high", retrieval_count=1, answer="這一定是對的。"),
    )

    print()
    if FAILURES:
        print(f"{len(FAILURES)} 項規則沒有通過：{FAILURES}")
        raise SystemExit(1)

    print("全部規則驗證通過。")


if __name__ == "__main__":
    main()
