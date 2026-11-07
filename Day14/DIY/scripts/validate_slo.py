"""
SLI Classification Validator

This script validates the SLI classifier against the test fixtures defined
in the Day 14 article.

The classification is based purely on the AskEvent dataclass and the
is_sli_eligible() and is_good_event() functions — with no external dependencies.

This is a specification check, not a production verification.
Run without needing any external services or API keys.

Expected output from Day 14 article (section ④, line 577-583):
  grounded_answer {'eligible': True, 'good': True}
  honest_unknown {'eligible': True, 'good': True}
  provider_timeout {'eligible': True, 'good': False}
  http_200_but_invalid {'eligible': True, 'good': False}
  malformed_payload {'eligible': False, 'good': False}
  system_denied_user {'eligible': True, 'good': False}
"""

from app.slo_spec import is_sli_eligible, is_good_event, CASES


def main():
    print("=" * 80)
    print("Day 14 DIY: SLI Classification Validator")
    print("=" * 80)
    print()
    print("Testing SLI classification fixtures from Day 14 article...")
    print()

    # Expected results from Day 14 article
    expected_results = {
        "grounded_answer": (True, True),
        "honest_unknown": (True, True),
        "provider_timeout": (True, False),
        "http_200_but_invalid": (True, False),
        "malformed_payload": (False, False),
        "system_denied_user": (True, False),
    }

    all_passed = True

    for name, event in CASES.items():
        eligible = is_sli_eligible(event)
        good = is_good_event(event)

        expected_eligible, expected_good = expected_results[name]

        matches = (eligible == expected_eligible) and (good == expected_good)
        status = "✓" if matches else "✗"

        print(f"{status} {name}")
        print(f"    Result:   eligible={eligible}, good={good}")
        print(f"    Expected: eligible={expected_eligible}, good={expected_good}")

        if not matches:
            print("    ⚠️  MISMATCH!")
            all_passed = False
        print()

    print("-" * 80)
    if all_passed:
        print("✅ All 6 test fixtures passed!")
        print()
        print("SLI Classification Results (Article Figure from line 266-273):")
        print()
        print("| fixture | eligible | good | 原因 |")
        print("| --- | --- | --- | --- |")
        print("| `grounded_answer` | `True` | `True` | 合法請求、契約完整、在門檻內完成 |")
        print("| `honest_unknown` | `True` | `True` | 產品允許誠實拒答，且回應格式完整 |")
        print("| `provider_timeout` | `True` | `False` | 使用者有有效需求，服務未在門檻內交付 |")
        print("| `http_200_but_invalid` | `True` | `False` | transport 成功不等於 response contract 成功 |")
        print("| `malformed_payload` | `False` | `False` | 此範例將無效請求排除於 availability 分母 |")
        print("| `system_denied_user` | `True` | `False` | 系統造成的拒絕應被看見 |")
    else:
        print("❌ Some test fixtures failed - review classification logic")

    print()
    print("=" * 80)
    print("Checklist (from Day 14 article section ③, line 756-761):")
    print("=" * 80)
    print()
    print("- [x] SLI、SLO、SLA 能各用一句話區分（見 slo.md）")
    print("- [x] SLI 有明確分子、分母、排除與資料來源（見 slo.md）")
    print("- [x] 尚未取得資料的數字標示為假設（見 slo.md）")
    print("- [x] spec 有 owner 與下一次檢視日期欄位（見 slo.md）")
    print()
    print("This validator demonstrates the SLI classification logic following")
    print("the article's pure-Python approach (no framework dependencies).")
    print()
    print("Note: This is a specification check, NOT a production SLI measurement.")
    print("Production measurement requires integration with Prometheus/Loki metrics.")
    print()


if __name__ == "__main__":
    main()
