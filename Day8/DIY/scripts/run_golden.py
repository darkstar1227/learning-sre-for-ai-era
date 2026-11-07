import asyncio
import json
from pathlib import Path

from pydantic import ValidationError

from app.evaluation import evaluate_ask
from app.schemas import AskResponse


GOLDEN_DATASET_PATH = Path("data/golden_dataset.json")


async def run_case(
    case: dict,
) -> dict:
    try:
        response: AskResponse = await evaluate_ask(
            case["question"],
        )

    except ValidationError:
        return {
            **case,
            "classification": "Wrong format",
            "detail": "response did not match AskResponse schema",
        }

    except Exception as exc:
        return {
            **case,
            "classification": "Failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }

    allowed = set(case["allowed_source_ids"])
    actual = set(response.sources)

    if response.answer_status != case["expected_answer_status"]:
        classification = "Unsupported"
        detail = (
            f"expected answer_status={case['expected_answer_status']!r}, "
            f"got {response.answer_status!r}"
        )
    elif allowed and not actual.issubset(allowed):
        classification = "Unsupported"
        detail = f"cited sources {sorted(actual)} not within allowed {sorted(allowed)}"
    elif response.quality_status != "pass" and case["expected_facts"]:
        classification = "Quality regression"
        detail = f"quality_status={response.quality_status!r}, answer={response.answer!r}"
    else:
        classification = "Correct (rule-based checks only — content still needs manual review)"
        detail = (
            f"quality_status={response.quality_status!r}, "
            f"safety_status={response.safety_status!r}, "
            f"answer={response.answer!r}"
        )

    return {
        **case,
        "classification": classification,
        "detail": detail,
    }


async def main() -> None:
    cases = json.loads(
        GOLDEN_DATASET_PATH.read_text(),
    )

    results = await asyncio.gather(
        *(run_case(case) for case in cases)
    )

    for result in results:
        print(
            f"[{result['classification']}] {result['id']}: {result['detail']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
