from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class Deadline:
    expires_at: float

    @classmethod
    def after_ms(cls, timeout_ms: int) -> "Deadline":
        return cls(expires_at=monotonic() + timeout_ms / 1_000)

    def remaining_ms(self) -> int:
        remaining = int((self.expires_at - monotonic()) * 1_000)
        return max(0, remaining)


def dependency_timeout_ms(deadline: Deadline, reserve_ms: int) -> int:
    remaining = deadline.remaining_ms() - reserve_ms
    if remaining <= 0:
        raise TimeoutError("service deadline exhausted")
    return remaining
