from itertools import count

from fastapi import FastAPI
from pydantic import BaseModel

from .telemetry import configure_tracing
from .workflow import answer_question


configure_tracing()
app = FastAPI()
request_sequence = count(1)


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(payload: AskRequest) -> dict[str, str]:
    request_id = f"local-{next(request_sequence)}"
    result = answer_question(request_id, payload.question)
    return {
        "request_id": request_id,
        "answer": result.answer,
        "task_status": result.task_status,
        "quality_status": result.quality_status,
    }
