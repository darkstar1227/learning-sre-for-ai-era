"""
Triage decision table implementation.

This module provides structured signal-to-route mapping
that mirrors the decision table from Day26.
"""

from dataclasses import dataclass
from typing import Optional
from app.models import TriageRoute


@dataclass
class TriageTableRow:
    """A single row in the alerting triage decision table."""

    signal: str
    """Name of the signal being monitored"""

    impact: str
    """Scope and severity of impact"""

    route: TriageRoute
    """Where this signal should be routed"""

    owner: str
    """Responsible team or person"""

    initial_action: str
    """What the owner should do first"""

    runbook: Optional[str] = None
    """Link to runbook or documentation"""


def get_example_triage_table() -> list[TriageTableRow]:
    """
    Returns the example triage table from Day26.md.

    This is the baseline table that must distinguish between:
    - Pager signals: wide-impact, actionable, time-sensitive
    - Review queue signals: quality/performance trends, needs investigation
    - Security signals: high-risk harm, unauthorized actions, data exposure
    """
    return [
        # Signals that trigger pager (immediate on-call escalation)
        TriageTableRow(
            signal="model timeout 快速上升且 SLO burn",
            impact="廣泛",
            route=TriageRoute.PAGER,
            owner="on-call",
            initial_action="查詢 provider status，評估降級方案",
            runbook="https://wiki.example.com/runbooks/model-provider-outage"
        ),

        # Signals that go to evaluation queue
        TriageTableRow(
            signal="citation-valid ratio 下降",
            impact="未知（需調查）",
            route=TriageRoute.EVALUATION_QUEUE,
            owner="model-owner",
            initial_action="比對版本與樣本，進行 root cause analysis",
            runbook="https://wiki.example.com/runbooks/quality-regression"
        ),

        # Signals that trigger security review
        TriageTableRow(
            signal="高風險 tool action 被拒絕",
            impact="安全風險",
            route=TriageRoute.SECURITY_REVIEW,
            owner="security-owner",
            initial_action="保留證據、停用 action、檢查 scope",
            runbook="https://wiki.example.com/runbooks/security-incident"
        ),
    ]


def get_extended_examples() -> list[TriageTableRow]:
    """
    Extended examples showing how to apply the triage framework
    to real product signals beyond the Day26 baseline.
    """
    return [
        # Queue backlog
        TriageTableRow(
            signal="inference queue backlog > 10k",
            impact="廣泛使用者體驗降級（延遲 15+ 分鐘）",
            route=TriageRoute.PAGER,
            owner="on-call",
            initial_action="檢查 GPU 利用率、啟動 auto-scaling、評估流量降級",
            runbook="https://wiki.example.com/runbooks/queue-saturation"
        ),

        # Single token distribution anomaly (not actionable, needs investigation)
        TriageTableRow(
            signal="token distribution shift (single batch)",
            impact="未知（單一樣本，無統計顯著性）",
            route=TriageRoute.EVALUATION_QUEUE,
            owner="model-owner",
            initial_action="檢查樣本特性、比對多日基線分布",
            runbook="https://wiki.example.com/runbooks/model-monitoring"
        ),

        # Evaluator disagreement
        TriageTableRow(
            signal="evaluator disagreement on single response",
            impact="單一樣本，無使用者影響",
            route=TriageRoute.EVALUATION_QUEUE,
            owner="evaluation-team",
            initial_action="記錄到 evaluation 隊列、後續 batch 分析",
            runbook="https://wiki.example.com/runbooks/eval-process"
        ),

        # Tool refusal (safety)
        TriageTableRow(
            signal="unauthorized database delete prevented",
            impact="安全風險（未授權破壞性動作被攔截）",
            route=TriageRoute.SECURITY_REVIEW,
            owner="security-owner",
            initial_action="保留完整 trace、檢查 prompt injection 可能",
            runbook="https://wiki.example.com/runbooks/tool-safety"
        ),

        # Data exposure
        TriageTableRow(
            signal="sensitive PII in model output",
            impact="安全風險（資料洩露）",
            route=TriageRoute.SECURITY_REVIEW,
            owner="security-owner",
            initial_action="立即停用該查詢路徑、審查 context window",
            runbook="https://wiki.example.com/runbooks/pii-exposure"
        ),

        # Provider outage
        TriageTableRow(
            signal="LLM API provider response time > 30s",
            impact="廣泛（所有請求延遲）",
            route=TriageRoute.PAGER,
            owner="on-call",
            initial_action="檢查 provider 狀態頁、啟動備用 provider",
            runbook="https://wiki.example.com/runbooks/provider-failover"
        ),

        # Cost anomaly (not immediate harm, but needs investigation)
        TriageTableRow(
            signal="token usage per request +300%",
            impact="經濟風險（成本上升），但不影響可用性",
            route=TriageRoute.EVALUATION_QUEUE,
            owner="platform-owner",
            initial_action="比對最近版本變更、檢查 prompt template",
            runbook="https://wiki.example.com/runbooks/token-cost"
        ),
    ]


def print_table(title: str, rows: list[TriageTableRow]) -> None:
    """Pretty-print a triage table."""
    print(f"\n{title}")
    print("=" * 140)
    print(f"{'Signal':<40} | {'Impact':<25} | {'Route':<18} | {'Owner':<18} | {'Initial Action':<35}")
    print("-" * 140)

    for row in rows:
        print(
            f"{row.signal:<40} | "
            f"{row.impact:<25} | "
            f"{row.route.value:<18} | "
            f"{row.owner:<18} | "
            f"{row.initial_action:<35}"
        )
    print()


def demo_triage_tables():
    """Display example triage tables."""

    # Baseline from Day26
    print("\n" + "=" * 140)
    print("AI Alerting Triage Decision Tables")
    print("Based on Day26: AI Alerting - 一筆幻覺不該叫醒所有人")
    print("=" * 140)

    baseline = get_example_triage_table()
    print_table("Baseline Table (from Day26)", baseline)

    extended = get_extended_examples()
    print_table("Extended Examples", extended)

    # Validation
    print("\n" + "=" * 140)
    print("Table Validation")
    print("=" * 140)

    all_rows = baseline + extended

    # Check 1: Every route should have an owner
    print("\n✓ Check 1: Every signal has a defined owner")
    for row in all_rows:
        if not row.owner:
            print(f"  ✗ {row.signal}: missing owner")
        else:
            print(f"  ✓ {row.signal}: owner={row.owner}")

    # Check 2: Pager signals should be actionable
    print("\n✓ Check 2: Pager signals should have clear initial actions")
    pager_signals = [r for r in all_rows if r.route == TriageRoute.PAGER]
    for row in pager_signals:
        if row.initial_action:
            print(f"  ✓ {row.signal}: action defined")
        else:
            print(f"  ✗ {row.signal}: missing initial action")

    # Check 3: All routes are properly defined
    print("\n✓ Check 3: All signals routed to valid destination")
    for row in all_rows:
        valid_routes = {TriageRoute.PAGER, TriageRoute.EVALUATION_QUEUE, TriageRoute.SECURITY_REVIEW}
        if row.route in valid_routes:
            print(f"  ✓ {row.signal}: route={row.route.value}")
        else:
            print(f"  ✗ {row.signal}: invalid route={row.route}")

    # Summary statistics
    print("\n" + "=" * 140)
    print("Summary Statistics")
    print("=" * 140)

    pager_count = len([r for r in all_rows if r.route == TriageRoute.PAGER])
    eval_count = len([r for r in all_rows if r.route == TriageRoute.EVALUATION_QUEUE])
    sec_count = len([r for r in all_rows if r.route == TriageRoute.SECURITY_REVIEW])

    print(f"\nTotal signals: {len(all_rows)}")
    print(f"  → pager: {pager_count} signals")
    print(f"  → evaluation_queue: {eval_count} signals")
    print(f"  → security_review: {sec_count} signals")

    print(f"\nOwners represented:")
    owners = set(r.owner for r in all_rows)
    for owner in sorted(owners):
        count = len([r for r in all_rows if r.owner == owner])
        print(f"  → {owner}: {count} signal(s)")

    print()
    return True


if __name__ == "__main__":
    try:
        success = demo_triage_tables()
        if success:
            print("✓ Triage table validation completed successfully")
        else:
            print("✗ Triage table validation failed")
            exit(1)
    except Exception as e:
        print(f"✗ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
