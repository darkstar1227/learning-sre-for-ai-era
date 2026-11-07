from dataclasses import dataclass
from enum import Enum


class OperationKind(str, Enum):
    READ = "read"
    WRITE = "write"


class FailureKind(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    TRANSIENT_NETWORK = "transient_network"
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DependencyRequest:
    request_id: str
    operation_kind: OperationKind
    idempotency_key: str | None
    deadline_ms: int


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    reason: str
    max_attempts: int


def decide_retry(
    request: DependencyRequest,
    failure: FailureKind,
) -> RetryDecision:
    if failure in {FailureKind.VALIDATION, FailureKind.AUTHORIZATION}:
        return RetryDecision(False, "deterministic_failure", 1)

    if request.operation_kind is OperationKind.WRITE:
        if not request.idempotency_key:
            return RetryDecision(False, "write_without_idempotency_key", 1)
        return RetryDecision(False, "verify_write_status_first", 1)

    if failure in {
        FailureKind.TIMEOUT,
        FailureKind.RATE_LIMIT,
        FailureKind.TRANSIENT_NETWORK,
    }:
        return RetryDecision(True, "bounded_transient_retry", 2)

    return RetryDecision(False, "unknown_failure", 1)
