from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChaosScenario(StrEnum):
    NONE = "none"
    PROVIDER_TIMEOUT = "provider-timeout"
    EMPTY_RETRIEVAL = "empty-retrieval"
    TOOL_SCHEMA_MISMATCH = "tool-schema-mismatch"


@dataclass(frozen=True)
class ChaosContext:
    scenario: ChaosScenario
    synthetic_tenant: bool


def parse_chaos_context(
    scenario_header: str | None,
    tenant_header: str | None,
) -> ChaosContext:
    if scenario_header is None:
        return ChaosContext(ChaosScenario.NONE, synthetic_tenant=False)

    if tenant_header != "synthetic-lab":
        raise PermissionError("chaos injection requires synthetic-lab tenant")

    try:
        scenario = ChaosScenario(scenario_header)
    except ValueError as exc:
        raise ValueError("unknown chaos scenario") from exc

    return ChaosContext(scenario, synthetic_tenant=True)
