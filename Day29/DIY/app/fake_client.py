from dataclasses import dataclass
from time import sleep


@dataclass
class FakeModelClient:
    latency_seconds: float = 0.0
    fail_with_timeout: bool = False

    def call(self, *, timeout_ms: int) -> dict[str, str]:
        sleep(self.latency_seconds)
        if self.fail_with_timeout:
            raise TimeoutError("simulated provider timeout")
        if self.latency_seconds * 1_000 > timeout_ms:
            raise TimeoutError("simulated client deadline")
        return {"answer": "simulated grounded answer"}


SCENARIOS = {
    "healthy": {
        "latency_seconds": 0.05,
        "fail_with_timeout": False,
    },
    "slow_but_within_deadline": {
        "latency_seconds": 0.15,
        "fail_with_timeout": False,
    },
    "deadline_exhausted": {
        "latency_seconds": 0.50,
        "fail_with_timeout": False,
    },
    "hard_timeout": {
        "latency_seconds": 0.01,
        "fail_with_timeout": True,
    },
}
