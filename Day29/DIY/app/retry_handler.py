from time import sleep

from app.backoff import backoff_seconds
from app.deadline import Deadline, dependency_timeout_ms


def call_with_retry(request, deadline: Deadline, client):
    last_error = None

    for attempt in range(2):
        try:
            timeout_ms = dependency_timeout_ms(deadline, reserve_ms=100)
            return client.call(timeout_ms=timeout_ms)
        except TimeoutError as error:
            last_error = error
            delay = backoff_seconds(attempt)
            if deadline.remaining_ms() <= int(delay * 1_000) + 100:
                break
            sleep(delay)

    raise RuntimeError("bounded retry exhausted") from last_error
