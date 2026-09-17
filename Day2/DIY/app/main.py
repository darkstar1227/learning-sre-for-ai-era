import asyncio
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app

from app.logging import logger
from app.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)
from app.telemetry import configure_tracing


configure_tracing()

app = FastAPI(
    title="Learning SRE for the AI Era — Day 02 SRE Lab",
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
    delay_ms: int = 0,
    fail: bool = False,
) -> dict[str, str]:

    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    if fail:
        raise HTTPException(
            status_code=500,
            detail="Injected failure",
        )

    return {
        "message": "SRE Lab is running",
        "timestamp": datetime.now(UTC).isoformat(),
    }
