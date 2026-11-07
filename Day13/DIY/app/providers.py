from app.models import ModelResult, ModelUnavailable


class PrimaryFake:
    name = "primary-fake"

    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail

    def generate(self, prompt: str, timeout_seconds: float) -> ModelResult:
        if self.should_fail:
            raise ModelUnavailable("simulated primary timeout")
        return ModelResult(text="primary test answer", provider=self.name)


class FallbackFake:
    name = "fallback-fake"

    def generate(self, prompt: str, timeout_seconds: float) -> ModelResult:
        return ModelResult(
            text="fallback test answer",
            provider=self.name,
            degraded=True,
        )
