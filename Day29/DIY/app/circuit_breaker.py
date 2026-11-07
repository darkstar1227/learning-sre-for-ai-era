from dataclasses import dataclass
from enum import Enum
from time import monotonic


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_after_seconds: float = 10.0
    failures: int = 0
    opened_at: float | None = None

    def state(self) -> BreakerState:
        if self.opened_at is None:
            return BreakerState.CLOSED
        if monotonic() - self.opened_at >= self.reset_after_seconds:
            return BreakerState.HALF_OPEN
        return BreakerState.OPEN

    def allow_call(self) -> bool:
        return self.state() is not BreakerState.OPEN

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = monotonic()
