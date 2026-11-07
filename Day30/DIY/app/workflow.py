from dataclasses import dataclass

from app.chaos import ChaosContext, ChaosScenario
from app.providers import ModelProvider, ProviderTimeout


@dataclass(frozen=True)
class AskResult:
    technical_status: str
    workflow_status: str
    task_status: str
    quality_status: str
    safety_status: str
    degraded: bool
    answer: str | None
    reason: str | None


provider = ModelProvider()


def retrieve_documents(question: str, chaos: ChaosContext) -> list[dict]:
    if chaos.scenario is ChaosScenario.EMPTY_RETRIEVAL:
        return []

    return [
        {
            "document_id": "synthetic-policy-v1",
            "title": "Synthetic Remote Work Policy",
            "content": "Synthetic content for an isolated lab.",
        }
    ]


def build_prompt(question: str, documents: list[dict]) -> str:
    context = "\n".join([doc.get("content", "") for doc in documents])
    return f"""Based on the following context:
{context}

Answer this question: {question}"""


def answer_workflow(question: str, chaos: ChaosContext) -> AskResult:
    documents = retrieve_documents(question, chaos)

    if not documents:
        return AskResult(
            technical_status="completed",
            workflow_status="insufficient_context",
            task_status="not_completed",
            quality_status="not_grounded",
            safety_status="no_tool_action",
            degraded=False,
            answer=None,
            reason="retrieval_empty",
        )

    try:
        reply = provider.generate(build_prompt(question, documents), chaos)
    except ProviderTimeout:
        return AskResult(
            technical_status="degraded",
            workflow_status="provider_unavailable",
            task_status="not_completed",
            quality_status="not_evaluated",
            safety_status="no_tool_action",
            degraded=True,
            answer=None,
            reason="model_provider_timeout",
        )

    return AskResult(
        technical_status="completed",
        workflow_status="completed",
        task_status="completed",
        quality_status="grounded",
        safety_status="no_tool_action",
        degraded=False,
        answer=reply.text,
        reason=None,
    )
