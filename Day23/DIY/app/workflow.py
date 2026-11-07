from dataclasses import dataclass
from hashlib import sha256

from .telemetry import tracer


@dataclass
class AskResult:
    answer: str
    task_status: str
    quality_status: str


def stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def retrieve(question: str) -> list[dict[str, str]]:
    with tracer.start_as_current_span("retrieval.search") as span:
        span.set_attribute("retrieval.index_version", "handbook-demo-v1")
        span.set_attribute("retrieval.query_hash", stable_hash(question))
        documents = [
            {
                "document_id": "remote-work-policy",
                "text": "遠端工作需依公司政策與主管核准流程辦理。",
            }
        ]
        span.set_attribute("retrieval.result_count", len(documents))
        span.set_attribute("workflow.outcome", "ok")
        return documents


def call_model(question: str, documents: list[dict[str, str]]) -> str:
    with tracer.start_as_current_span("model.chat") as span:
        span.set_attribute("model.provider", "mock")
        span.set_attribute("model.name", "policy-demo")
        span.set_attribute("model.route", "primary")
        span.set_attribute("prompt.version", "policy-qa-v1")
        span.set_attribute("input_token_count", 42)
        span.set_attribute("output_token_count", 18)
        span.set_attribute("workflow.outcome", "ok")
        return "依遠端工作政策，請依主管核准流程辦理。"


def validate(answer: str, documents: list[dict[str, str]]) -> str:
    with tracer.start_as_current_span("answer.validate") as span:
        grounded = "主管核准" in answer and bool(documents)
        span.set_attribute("quality.status", "pass" if grounded else "fail")
        span.set_attribute("safety.status", "pass")
        span.set_attribute("citation.valid", grounded)
        span.set_attribute("workflow.outcome", "ok" if grounded else "failed")
        return "pass" if grounded else "fail"


def answer_question(request_id: str, question: str) -> AskResult:
    with tracer.start_as_current_span("POST /ask") as root:
        root.set_attribute("request.id", request_id)
        root.set_attribute("workflow.name", "policy-qa")
        root.set_attribute("workflow.version", "v1")
        root.set_attribute("technical.status", "ok")

        with tracer.start_as_current_span("prompt.build") as prompt_span:
            prompt_span.set_attribute("prompt.version", "policy-qa-v1")
            prompt_span.set_attribute("question_hash", stable_hash(question))
            prompt_span.set_attribute("workflow.outcome", "ok")

        documents = retrieve(question)
        answer = call_model(question, documents)
        quality_status = validate(answer, documents)

        task_status = "completed" if quality_status == "pass" else "failed"
        root.set_attribute("workflow.status", "completed")
        root.set_attribute("quality.status", quality_status)
        root.set_attribute("task.status", task_status)
        return AskResult(answer, task_status, quality_status)
