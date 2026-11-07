import json
from app.deadline import Deadline
from app.fake_client import FakeModelClient, SCENARIOS
from app.retry_handler import call_with_retry


def run_scenario(name: str, config: dict[str, object]) -> None:
    client = FakeModelClient(**config)
    deadline = Deadline.after_ms(300)

    try:
        result = call_with_retry(
            request=None,
            deadline=deadline,
            client=client,
        )
        print(json.dumps({
            "scenario": name,
            "result": result,
            "outcome": "completed",
            "remaining_deadline_ms": deadline.remaining_ms(),
        }))
    except RuntimeError as error:
        print(json.dumps({
            "scenario": name,
            "error": str(error),
            "outcome": "degraded_or_failed",
            "remaining_deadline_ms": deadline.remaining_ms(),
        }))
    except TimeoutError as error:
        print(json.dumps({
            "scenario": name,
            "error": str(error),
            "outcome": "timeout",
            "remaining_deadline_ms": deadline.remaining_ms(),
        }))


if __name__ == "__main__":
    print("=== Running Day29 DIY Scenario Tests ===")
    print()
    for scenario_name, scenario_config in SCENARIOS.items():
        run_scenario(scenario_name, scenario_config)
        print()
