from fastapi import FastAPI, HTTPException

from app.llm import ask_llm
from app.schemas import AskRequest, AskResponse


app = FastAPI(
    title="Learning SRE for the AI Era — Day 01",
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
        result = await ask_llm(
            request.question,
        )

        return AskResponse(**result)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM request failed",
        ) from exc
