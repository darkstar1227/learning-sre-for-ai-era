from random import uniform


def backoff_seconds(
    attempt_number: int,
    *,
    base_seconds: float = 0.2,
    cap_seconds: float = 2.0,
) -> float:
    exponential_cap = min(
        cap_seconds,
        base_seconds * (2 ** attempt_number),
    )
    return uniform(0, exponential_cap)
