#!/usr/bin/env python3
"""
測試 Day11 DIY 的核心機制

不需要啟動 FastAPI 服務，直接測試 failure mode 邏輯。
對應文章情境一與情境二。
"""

import asyncio
import sys
from app.main import (
    is_retriable,
    backoff_with_jitter,
    policy_provider,
    call_provider_with_budget,
)


async def test_is_retriable():
    """測試 is_retriable() 函數"""
    print("\n[Test] is_retriable() 判斷邏輯")

    # 可重試的錯誤
    assert is_retriable(TimeoutError()) == True, "TimeoutError 應該可重試"
    assert is_retriable(ConnectionError()) == True, "ConnectionError 應該可重試"

    # 不可重試的錯誤
    assert is_retriable(ValueError()) == False, "ValueError 不應重試"
    assert is_retriable(RuntimeError()) == False, "RuntimeError 不應重試"

    print("  ✅ is_retriable() 邏輯正確")


async def test_backoff_with_jitter():
    """測試 backoff_with_jitter() 函數"""
    print("\n[Test] backoff_with_jitter() 指數退避 + jitter")

    # 第一次重試：0 ~ 0.05 秒
    delay_0 = backoff_with_jitter(0)
    assert 0 <= delay_0 <= 0.05, f"Attempt 0 應在 0-0.05s 間，實測 {delay_0}"

    # 第二次重試：0 ~ 0.10 秒
    delay_1 = backoff_with_jitter(1)
    assert 0 <= delay_1 <= 0.10, f"Attempt 1 應在 0-0.10s 間，實測 {delay_1}"

    print(f"  ✅ Attempt 0: {delay_0:.4f}s")
    print(f"  ✅ Attempt 1: {delay_1:.4f}s")


async def test_normal_provider():
    """測試正常 provider 呼叫"""
    print("\n[Test] 正常 policy_provider 呼叫")

    result = await policy_provider("normal")
    assert result["answer"] == "Remote work requires manager approval."
    assert result["source"] == "company-policy-remote-work"

    print("  ✅ 正常回應成功")


async def test_slow_provider():
    """測試慢 provider 與 timeout"""
    print("\n[Test] 慢 provider 與 asyncio.wait_for() timeout")

    try:
        # 應該超過 CLIENT_TIMEOUT_SECONDS (0.25s)
        await asyncio.wait_for(
            policy_provider("slow"),
            timeout=0.25,
        )
        print("  ❌ FAILED: 應該 timeout")
        return False
    except TimeoutError:
        print("  ✅ 正確拋出 TimeoutError")


async def test_unavailable_provider():
    """測試不可用 provider"""
    print("\n[Test] 不可用 policy_provider")

    try:
        await policy_provider("unavailable")
        print("  ❌ FAILED: 應該拋出 ConnectionError")
        return False
    except ConnectionError as e:
        print(f"  ✅ 正確拋出 ConnectionError: {e}")


async def test_provider_with_budget_unavailable():
    """測試 call_provider_with_budget() 在不可用時的重試行為"""
    print("\n[Test] call_provider_with_budget() 帶 retry budget 的重試")

    try:
        await call_provider_with_budget("unavailable")
        print("  ❌ FAILED: 應該在有限重試後失敗")
        return False
    except ConnectionError as e:
        print(f"  ✅ 有限重試後正確失敗: {e}")


async def main():
    """執行所有測試"""
    print("=" * 70)
    print("Day11 DIY - Failure Mode 邏輯測試")
    print("=" * 70)

    try:
        await test_is_retriable()
        await test_backoff_with_jitter()
        await test_normal_provider()
        await test_slow_provider()
        await test_unavailable_provider()
        await test_provider_with_budget_unavailable()

        print("\n" + "=" * 70)
        print("所有測試通過 ✅")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
