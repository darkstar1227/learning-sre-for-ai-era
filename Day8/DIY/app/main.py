from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app

from app.evaluation import evaluate_ask
from app.schemas import AskRequest, AskResponse


app = FastAPI(
    title="Learning SRE for the AI Era — Day 08 Reliability/Quality/Safety",
    version="0.1.0",
)

app.mount("/metrics", make_asgi_app())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.post(
    "/ask",
    response_model=AskResponse,
)
async def ask(
    request: AskRequest,
) -> AskResponse:

    try:
        return await evaluate_ask(
            request.question,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM request failed",
        ) from exc
