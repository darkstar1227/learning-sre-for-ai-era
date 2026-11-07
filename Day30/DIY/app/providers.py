from dataclasses import dataclass

from app.chaos import ChaosContext, ChaosScenario


class ProviderTimeout(Exception):
    """A simulated upstream timeout for an isolated chaos run."""


@dataclass(frozen=True)
class ModelReply:
    text: str
    model_name: str


class ModelProvider:
    def generate(self, prompt: str, chaos: ChaosContext) -> ModelReply:
        if chaos.scenario is ChaosScenario.PROVIDER_TIMEOUT:
            raise ProviderTimeout("simulated provider timeout")

        return ModelReply(
            text="Synthetic baseline answer.",
            model_name="fake-model-v1",
        )
