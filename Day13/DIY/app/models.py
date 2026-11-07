from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelResult:
    text: str
    provider: str
    degraded: bool = False


class ModelUnavailable(Exception):
    pass


class ModelClient(Protocol):
    name: str

    def generate(self, prompt: str, timeout_seconds: float) -> ModelResult:
        ...
