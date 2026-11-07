from threading import BoundedSemaphore


class AdmissionGate:
    def __init__(self, max_in_flight: int) -> None:
        self._slots = BoundedSemaphore(max_in_flight)

    def try_enter(self) -> bool:
        return self._slots.acquire(blocking=False)

    def leave(self) -> None:
        self._slots.release()
