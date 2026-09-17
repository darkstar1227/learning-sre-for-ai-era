import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import make_asgi_app

from app.logging import logger
from app.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)
from app.telemetry import configure_tracing


configure_tracing()

tracer = trace.get_tracer(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sre:sre@postgres:5432/sre_lab",
)

app = FastAPI(
    title="Learning SRE for the AI Era — Day 03 Failure Injection",
    version="0.1.0",
)

FastAPIInstrumentor.instrument_app(
    app,
)

metrics_app = make_asgi_app()
app.mount(
    "/metrics",
    metrics_app,
)


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next,
):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid4()),
    )

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next,
):
    route = request.url.path
    method = request.method

    HTTP_REQUESTS_IN_PROGRESS.labels(
        method=method,
        route=route,
    ).inc()

    started_at = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    except Exception:
        status_code = 500
        raise

    finally:
        duration = time.perf_counter() - started_at

        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=method,
            route=route,
        ).dec()

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            route=route,
        ).observe(duration)

        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status_code=str(status_code),
        ).inc()

        logger.info(
            "request completed",
            extra={
                "service": "api",
                "request_id": getattr(request.state, "request_id", None),
                "method": method,
                "path": route,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {
        "status": "ready",
    }


@app.get("/api/demo")
async def demo(
    delay_ms: Annotated[
        int,
        Query(ge=0, le=10_000),
    ] = 0,
    fail: bool = False,
) -> dict[str, str]:
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    if fail:
        try:
            raise RuntimeError(
                "Injected application failure"
            )
        except RuntimeError:
            logger.exception(
                "injected application failure"
            )
            raise

    return {
        "message": "SRE Lab is running",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/database")
async def database_demo() -> dict[str, str | int]:
    with tracer.start_as_current_span("postgres.select_one") as span:
        try:
            connection = await psycopg.AsyncConnection.connect(
                DATABASE_URL,
                connect_timeout=1,
            )

            async with connection:
                async with connection.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    row = await cursor.fetchone()

            return {
                "status": "ok",
                "result": row[0],
            }

        except psycopg.Error as exc:
            span.set_status(
                Status(
                    StatusCode.ERROR,
                    "postgres unavailable",
                )
            )
            span.set_attribute(
                "error.type",
                type(exc).__qualname__,
            )

            logger.exception(
                "database request failed",
                extra={
                    "dependency": "postgres",
                },
            )

            raise HTTPException(
                status_code=503,
                detail="Database unavailable",
            ) from exc


def require_chaos_enabled() -> None:
    if os.getenv("CHAOS_ENABLED") != "true":
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )


@app.get("/api/consume-memory")
async def consume_memory(
    megabytes: Annotated[
        int,
        Query(ge=1, le=512),
    ] = 300,
) -> dict[str, int]:
    require_chaos_enabled()

    chunks: list[bytearray] = []

    for _ in range(megabytes):
        chunk = bytearray(1024 * 1024)

        # Touch each memory page so the allocation becomes resident.
        chunk[::4096] = b"x" * len(chunk[::4096])

        chunks.append(chunk)
        await asyncio.sleep(0)

    await asyncio.sleep(30)

    return {
        "allocated_megabytes": len(chunks),
    }
