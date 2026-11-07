"""Test resilience components: deadline, retry decision, circuit breaker, admission gate"""
import json
from time import sleep

from app.admission_gate import AdmissionGate
from app.circuit_breaker import CircuitBreaker, BreakerState
from app.deadline import Deadline, dependency_timeout_ms
from app.retry_decision import (
    decide_retry,
    DependencyRequest,
    FailureKind,
    OperationKind,
)


def test_deadline():
    print("=== Test 1: Deadline and timeout calculation ===")
    deadline = Deadline.after_ms(300)
    print(f"Initial remaining: {deadline.remaining_ms()}ms")

    sleep(0.1)
    remaining = deadline.remaining_ms()
    print(f"After 100ms sleep: {remaining}ms (should be ~200ms)")

    try:
        timeout = dependency_timeout_ms(deadline, reserve_ms=150)
        print(f"Dependency timeout with 150ms reserve: {timeout}ms")
    except TimeoutError as e:
        print(f"Timeout error: {e}")

    print()


def test_retry_decision():
    print("=== Test 2: Retry decision logic ===")

    # Test 1: Read operation with timeout
    req_read = DependencyRequest(
        request_id="req1",
        operation_kind=OperationKind.READ,
        idempotency_key=None,
        deadline_ms=300,
    )
    decision = decide_retry(req_read, FailureKind.TIMEOUT)
    print(f"READ + TIMEOUT: should_retry={decision.should_retry}, reason={decision.reason}")

    # Test 2: Write operation without idempotency key
    req_write_no_key = DependencyRequest(
        request_id="req2",
        operation_kind=OperationKind.WRITE,
        idempotency_key=None,
        deadline_ms=300,
    )
    decision = decide_retry(req_write_no_key, FailureKind.TIMEOUT)
    print(f"WRITE(no key) + TIMEOUT: should_retry={decision.should_retry}, reason={decision.reason}")

    # Test 3: Write operation with idempotency key
    req_write_with_key = DependencyRequest(
        request_id="req3",
        operation_kind=OperationKind.WRITE,
        idempotency_key="idempotency-123",
        deadline_ms=300,
    )
    decision = decide_retry(req_write_with_key, FailureKind.TIMEOUT)
    print(f"WRITE(with key) + TIMEOUT: should_retry={decision.should_retry}, reason={decision.reason}")

    # Test 4: Validation error
    decision = decide_retry(req_read, FailureKind.VALIDATION)
    print(f"READ + VALIDATION: should_retry={decision.should_retry}, reason={decision.reason}")

    print()


def test_circuit_breaker():
    print("=== Test 3: Circuit breaker state transitions ===")

    breaker = CircuitBreaker(failure_threshold=3, reset_after_seconds=2.0)

    print(f"Initial state: {breaker.state()}")
    assert breaker.allow_call() is True

    # Record 3 failures
    for i in range(3):
        breaker.record_failure()
        print(f"After failure {i+1}: state={breaker.state()}, allow_call={breaker.allow_call()}")

    # Try to call when open
    print(f"Breaker is open, allow_call={breaker.allow_call()} (should be False)")

    # Record success should reset it
    breaker.record_success()
    print(f"After success: state={breaker.state()}, allow_call={breaker.allow_call()}")

    print()


def test_admission_gate():
    print("=== Test 4: Admission gate capacity control ===")

    gate = AdmissionGate(max_in_flight=2)

    # Enter 2 requests (should succeed)
    success1 = gate.try_enter()
    success2 = gate.try_enter()
    print(f"Request 1: {success1}, Request 2: {success2}")

    # Try to enter 3rd (should fail)
    success3 = gate.try_enter()
    print(f"Request 3 (should fail): {success3}")

    # Leave 1, should now succeed
    gate.leave()
    success3_retry = gate.try_enter()
    print(f"Request 3 after 1 left: {success3_retry}")

    print()


if __name__ == "__main__":
    print("=== Day29 DIY Component Tests ===")
    print()

    test_deadline()
    test_retry_decision()
    test_circuit_breaker()
    test_admission_gate()

    print("All component tests completed!")
