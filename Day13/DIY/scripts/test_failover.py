#!/usr/bin/env python3
"""
Test failover routing logic from Day 13.

Test scenarios from Day13.md section ⑦ (fifth step):
1. Primary success - direct path completes
2. Allowed task with primary failure - switches to fallback
3. Sensitive task with primary failure - rejects fallback, returns unavailable
"""

import sys

from app.providers import FallbackFake, PrimaryFake
from app.router import generate_with_fallback


def test_primary_success() -> None:
    outcome = generate_with_fallback(
        request_id="req-primary-ok",
        task_type="policy_question",
        prompt="test",
        primary=PrimaryFake(should_fail=False),
        fallback=FallbackFake(),
    )
    assert outcome.status == "completed", f"Expected 'completed', got '{outcome.status}'"
    assert outcome.fallback_triggered is False, "Fallback should not be triggered"
    assert outcome.result is not None, "Result should not be None"
    assert outcome.result.provider == "primary-fake", f"Expected provider 'primary-fake', got '{outcome.result.provider}'"
    print("✓ test_primary_success PASSED")


def test_allowed_task_uses_fallback() -> None:
    outcome = generate_with_fallback(
        request_id="req-fallback-ok",
        task_type="policy_question",
        prompt="test",
        primary=PrimaryFake(should_fail=True),
        fallback=FallbackFake(),
    )
    assert outcome.status == "degraded_completed", f"Expected 'degraded_completed', got '{outcome.status}'"
    assert outcome.fallback_triggered is True, "Fallback should be triggered"
    assert outcome.result is not None, "Result should not be None"
    assert outcome.result.degraded is True, "Result should be marked degraded"
    assert outcome.result.provider == "fallback-fake", f"Expected provider 'fallback-fake', got '{outcome.result.provider}'"
    print("✓ test_allowed_task_uses_fallback PASSED")


def test_sensitive_task_does_not_fallback() -> None:
    outcome = generate_with_fallback(
        request_id="req-no-fallback",
        task_type="permission_change",
        prompt="test",
        primary=PrimaryFake(should_fail=True),
        fallback=FallbackFake(),
    )
    assert outcome.status == "unavailable", f"Expected 'unavailable', got '{outcome.status}'"
    assert outcome.fallback_triggered is False, "Fallback should not be triggered for sensitive tasks"
    assert outcome.result is None, "Result should be None when unavailable"
    print("✓ test_sensitive_task_does_not_fallback PASSED")


if __name__ == "__main__":
    try:
        test_primary_success()
        test_allowed_task_uses_fallback()
        test_sensitive_task_does_not_fallback()
        print("\n✅ All tests PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
