"""
故障注入模組

本模組實現文章 Day11 所述的各種 Failure Mode。
每個故障模式對應真實環境中的某種生產問題。
"""

import asyncio
import time
from typing import Callable, Any


class ChaosFailure(Exception):
    """故障注入異常"""

    pass


class TimeoutSimulation(ChaosFailure):
    """模擬 upstream timeout"""

    pass


class BadSchemaSimulation(ChaosFailure):
    """模擬 dependency 返回不符合 contract 的資料"""

    pass


class DependencyFailureSimulation(ChaosFailure):
    """模擬 dependency 完全不可用"""

    pass


class ResourceExhaustionSimulation(ChaosFailure):
    """模擬資源耗盡（連線池、記憶體等）"""

    pass


async def inject_chaos(
    chaos_mode: str | None, delay_ms: int = 0
) -> None:
    """
    根據 chaos_mode 注入故障。

    Args:
        chaos_mode: 故障模式
            - "timeout": 模擬上游超時（例如 LLM 呼叫超時）
            - "bad_schema": 模擬依賴返回不符合 contract 的資料
            - "dependency_fail": 模擬依賴服務不可用
            - "resource_exhaustion": 模擬資源耗盡
            - None: 無故障，正常執行
        delay_ms: 延遲毫秒數（用於模擬慢請求）
    """
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000.0)

    if chaos_mode == "timeout":
        raise TimeoutSimulation("LLM request timed out (simulated)")

    elif chaos_mode == "bad_schema":
        raise BadSchemaSimulation(
            "Dependency returned invalid schema (simulated)"
        )

    elif chaos_mode == "dependency_fail":
        raise DependencyFailureSimulation(
            "Dependency service is unavailable (simulated)"
        )

    elif chaos_mode == "resource_exhaustion":
        raise ResourceExhaustionSimulation(
            "Resource pool exhausted (simulated)"
        )


def map_chaos_to_http_status(exc: ChaosFailure) -> int:
    """
    根據故障類型對應 HTTP 狀態碼。

    這實現文章中「失敗後回什麼」的原則：
    不同的 Failure Mode 應映射到不同的客戶端結果。
    """
    if isinstance(exc, TimeoutSimulation):
        # timeout 在客戶端看來應該是 504 Gateway Timeout
        # 但若 client 也有 timeout，可能收到的是連線重置
        return 504

    elif isinstance(exc, BadSchemaSimulation):
        # Dependency 返回壞資料 = 該服務可用但回答不對
        # 常見做法是 502 Bad Gateway（表示上游服務行為異常）
        return 502

    elif isinstance(exc, DependencyFailureSimulation):
        # Dependency 完全不可用 = 503 Service Unavailable
        return 503

    elif isinstance(exc, ResourceExhaustionSimulation):
        # 資源耗盡 = 暫時無法服務 = 503 Service Unavailable
        return 503

    else:
        return 500


def should_retry(exc: Exception) -> bool:
    """
    判斷異常是否應該重試。

    文章 Day11 強調：不是所有錯誤都該重試。
    - TimeoutSimulation: 可重試（可能暫時性故障）
    - BadSchemaSimulation: 不應重試（表示上游邏輯有問題）
    - DependencyFailureSimulation: 可重試（取決於業務判斷）
    - ResourceExhaustionSimulation: 應該降級，不該無限重試
    """
    if isinstance(exc, BadSchemaSimulation):
        # 4xx 等級的錯誤（邏輯問題）不應重試
        return False

    if isinstance(exc, TimeoutSimulation):
        # 5xx 等級的錯誤可能是暫時性的
        return True

    if isinstance(exc, DependencyFailureSimulation):
        # 可重試，但要搭配 backoff 與上限
        return True

    if isinstance(exc, ResourceExhaustionSimulation):
        # 資源耗盡通常表示系統過載，盲目重試會讓情況更糟
        # 應優先降級或 reject，避免 retry storm
        return False

    return False
