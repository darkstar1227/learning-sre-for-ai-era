"""
Day11 DIY: Production Failure Mode API

展示 deadline、timeout、retry amplification 與 degraded mode 的設計。
"""

import asyncio
import json
import logging
import random
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import AskRequest, AskResponse

app = FastAPI(title="Day11 Failure Mode Lab")
logger = logging.getLogger("sre_lab")
logging.basicConfig(level=logging.WARNING)

CLIENT_TIMEOUT_SECONDS = 0.25
MAX_RETRIES = 1
BASE_BACKOFF_SECONDS = 0.05
MAX_BACKOFF_SECONDS = 0.20


async def policy_provider(mode: str) -> dict[str, str]:
    """模擬 policy provider 依賴"""
    if mode == "slow":
        await asyncio.sleep(0.60)

    if mode == "unavailable":
        raise ConnectionError("simulated provider connection failure")

    return {
        "answer": "Remote work requires manager approval.",
        "source": "company-policy-remote-work",
    }


def emit(event: str, **fields: object) -> None:
    """發出結構化事件日誌"""
    logger.warning(json.dumps({"event": event, **fields}))


def is_retriable(error: Exception) -> bool:
    """判斷錯誤是否可重試"""
    return isinstance(error, (ConnectionError, TimeoutError))


def backoff_with_jitter(attempt: int) -> float:
    """計算帶 jitter 的退避時間"""
    ceiling = min(
        MAX_BACKOFF_SECONDS,
        BASE_BACKOFF_SECONDS * (2 ** attempt),
    )
    return random.uniform(0, ceiling)


async def call_provider_with_budget(mode: str) -> dict[str, str]:
    """
    呼叫 provider，帶有 retry budget 與 deadline 傳播。

    只允許一次重試，且檢查是否還有時間完成。
    """
    deadline = time.monotonic() + 0.80

    for attempt in range(MAX_RETRIES + 1):
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("request deadline exhausted")

            return await asyncio.wait_for(
                policy_provider(mode),
                timeout=min(CLIENT_TIMEOUT_SECONDS, remaining),
            )
        except Exception as exc:
            if not is_retriable(exc) or attempt == MAX_RETRIES:
                raise

            delay = backoff_with_jitter(attempt)
            if time.monotonic() + delay >= deadline:
                raise TimeoutError("no time left for retry") from exc

            emit(
                "dependency_retry_scheduled",
                dependency="policy_provider",
                retry_attempt=attempt + 1,
                backoff_ms=round(delay * 1000),
            )
            await asyncio.sleep(delay)

    raise AssertionError("unreachable")


@app.post("/ask")
async def ask(payload: AskRequest) -> dict[str, object]:
    """
    主要端點：展示 deadline、timeout、retry 與 response contract。

    情境一：慢 provider（failure_mode="slow"）
    - 觸發 TimeoutError
    - 回傳 HTTP 503 與明確的 unavailable response

    情境二：不可用 provider（failure_mode="unavailable"）
    - 搭配 call_provider_with_budget() 展示有限 retry
    - 最多兩次 attempt，然後失敗
    """
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    started_at = time.monotonic()

    try:
        result = await asyncio.wait_for(
            policy_provider(payload.failure_mode),
            timeout=CLIENT_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        elapsed_ms = round((time.monotonic() - started_at) * 1000)
        emit(
            "dependency_timeout",
            request_id=request_id,
            dependency="policy_provider",
            elapsed_ms=elapsed_ms,
            timeout_ms=int(CLIENT_TIMEOUT_SECONDS * 1000),
        )
        return JSONResponse(
            status_code=503,
            content={
                "answer_status": "unavailable",
                "technical_success": False,
                "degraded": False,
                "request_id": request_id,
                "reason": "policy_provider_timeout",
            },
        )
    except ConnectionError as exc:
        elapsed_ms = round((time.monotonic() - started_at) * 1000)
        emit(
            "dependency_connection_error",
            request_id=request_id,
            dependency="policy_provider",
            elapsed_ms=elapsed_ms,
        )
        return JSONResponse(
            status_code=503,
            content={
                "answer_status": "unavailable",
                "technical_success": False,
                "degraded": False,
                "request_id": request_id,
                "reason": "policy_provider_unavailable",
            },
        )

    elapsed_ms = round((time.monotonic() - started_at) * 1000)
    emit(
        "dependency_success",
        request_id=request_id,
        dependency="policy_provider",
        elapsed_ms=elapsed_ms,
    )
    return {
        **result,
        "answer_status": "answered",
        "technical_success": True,
        "degraded": False,
        "request_id": request_id,
    }


@app.post("/ask/with-retry")
async def ask_with_retry(payload: AskRequest) -> dict[str, object]:
    """
    展示帶 retry budget 的情況。

    與 /ask 不同的是，這個端點允許一次重試。
    用來演示情境二：retry amplification。
    """
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    started_at = time.monotonic()

    try:
        result = await call_provider_with_budget(payload.failure_mode)
    except TimeoutError as exc:
        elapsed_ms = round((time.monotonic() - started_at) * 1000)
        emit(
            "dependency_timeout",
            request_id=request_id,
            dependency="policy_provider",
            elapsed_ms=elapsed_ms,
            timeout_ms=int(CLIENT_TIMEOUT_SECONDS * 1000),
        )
        return JSONResponse(
            status_code=503,
            content={
                "answer_status": "unavailable",
                "technical_success": False,
                "degraded": False,
                "request_id": request_id,
                "reason": "policy_provider_timeout",
            },
        )
    except ConnectionError as exc:
        elapsed_ms = round((time.monotonic() - started_at) * 1000)
        emit(
            "dependency_connection_error",
            request_id=request_id,
            dependency="policy_provider",
            elapsed_ms=elapsed_ms,
        )
        return JSONResponse(
            status_code=503,
            content={
                "answer_status": "unavailable",
                "technical_success": False,
                "degraded": False,
                "request_id": request_id,
                "reason": "policy_provider_unavailable",
            },
        )

    elapsed_ms = round((time.monotonic() - started_at) * 1000)
    emit(
        "dependency_success",
        request_id=request_id,
        dependency="policy_provider",
        elapsed_ms=elapsed_ms,
    )
    return {
        **result,
        "answer_status": "answered",
        "technical_success": True,
        "degraded": False,
        "request_id": request_id,
    }
