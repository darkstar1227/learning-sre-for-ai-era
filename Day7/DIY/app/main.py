from fastapi import FastAPI, HTTPException

from app.llm import ask_grounded
from app.schemas import AskRequest, AskResponse


app = FastAPI(
    title="Learning SRE for the AI Era — Day 07 Grounded Q&A",
    version="0.1.0",
)


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
        return await ask_grounded(
            request.question,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM request failed",
        ) from exc
