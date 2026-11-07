#!/usr/bin/env python3
"""
Demonstration of the SlowDatabase fault injection example from Day10.md Step 1.

This script shows:
1. A simulated slow/failing database client
2. How it propagates as an Error (timeout/exception)
3. How to handle it gracefully to prevent user Failure

This is a code reference only; Day10.md did not execute this.
The exercise is for readers to adapt this pattern in their own FastAPI service.
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorClass(str, Enum):
    """Classifies errors for observability."""
    DATABASE_TIMEOUT = "database_timeout"
    DATABASE_NOT_FOUND = "database_not_found"
    DATABASE_UNAVAILABLE = "database_unavailable"


@dataclass
class QueryResult:
    """Result of a database query attempt."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[ErrorClass] = None
    error_message: str = ""


class SlowDatabase:
    """
    Simulated database client that can be configured to fail in different ways.
    Represents a FAULT: incorrect configuration or resource constraint.
    """

    def __init__(self, timeout_seconds: float = 2.0, fail_mode: Optional[str] = None):
        """
        Initialize with configurable timeout and failure mode.

        Args:
            timeout_seconds: How long to wait before timing out
            fail_mode: None (normal), "timeout", "not_found", or "unavailable"
        """
        self.timeout_seconds = timeout_seconds
        self.fail_mode = fail_mode
        self.call_count = 0
        self.error_count = 0

    def fetch_policy(self, policy_id: str) -> QueryResult:
        """
        Simulate fetching a policy by ID.

        Returns: QueryResult with success flag and error class if it failed.
        """
        self.call_count += 1

        # Simulate different failure modes
        if self.fail_mode == "timeout":
            self.error_count += 1
            # In real code, this would be: raise TimeoutError("database timeout after 2.0s")
            # Here we simulate the error and return it for this demo
            time.sleep(self.timeout_seconds + 0.1)  # Exceed timeout
            return QueryResult(
                success=False,
                error=ErrorClass.DATABASE_TIMEOUT,
                error_message=f"Database query exceeded {self.timeout_seconds}s timeout",
            )

        elif self.fail_mode == "not_found":
            self.error_count += 1
            return QueryResult(
                success=False,
                error=ErrorClass.DATABASE_NOT_FOUND,
                error_message=f"Policy {policy_id} not found in database",
            )

        elif self.fail_mode == "unavailable":
            self.error_count += 1
            return QueryResult(
                success=False,
                error=ErrorClass.DATABASE_UNAVAILABLE,
                error_message="Database connection refused (likely down for maintenance)",
            )

        # Normal case
        else:
            time.sleep(0.1)  # Simulate latency
            return QueryResult(
                success=True,
                data={"id": policy_id, "title": f"Policy {policy_id}", "version": "2025-01"},
            )


class AskWorkflow:
    """
    Simplified workflow that depends on the database.
    Shows how errors from dependencies propagate and can be mitigated.
    """

    def __init__(self, db: SlowDatabase, timeout_seconds: float = 5.0):
        self.db = db
        self.timeout_seconds = timeout_seconds
        self.requests = 0
        self.failures = 0

    def ask(self, question: str, policy_id: str) -> Dict:
        """
        Handle a user question about a policy.

        Returns:
            - If successful: {"status": "ok", "answer": "...", "policy_id": "..."}
            - If error occurs: {"status": "degraded", "message": "try again later"}
            - If failure: HTTP 502 would be returned by FastAPI handler
        """
        self.requests += 1
        user_request_id = f"req-{self.requests}"

        # STEP 1: Fetch policy from database
        # This is where the ERROR from database propagates
        result = self.db.fetch_policy(policy_id)

        # STEP 2: Handle the result
        # This is where we convert ERROR into user-safe response (mitigate FAILURE)
        if not result.success:
            self.failures += 1
            # ERROR: Database call failed
            # We have choices for FAILURE mitigation:
            # A) Explicit degradation (user knows to retry)
            # B) Cached response (user gets old answer)
            # C) Circuit breaker (prevent cascading)
            #
            # Here we choose option A: explicit degradation
            return {
                "status": "degraded",
                "request_id": user_request_id,
                "message": "Unable to retrieve policy at this time. Please try again in a moment.",
                "error_class": result.error,
            }

        # STEP 3: Generate answer (simulate LLM call)
        # In Day1, this would call Gemini
        policy = result.data
        answer = f"Based on {policy['title']} (v{policy['version']}), " f"the policy states: travel pre-approval required for trips over 5 days."

        return {
            "status": "ok",
            "request_id": user_request_id,
            "answer": answer,
            "policy_id": policy_id,
        }

    def metrics_summary(self) -> Dict:
        """Return simple metrics for observability."""
        return {
            "requests_total": self.requests,
            "failures_total": self.failures,
            "failure_rate": self.failures / max(1, self.requests),
            "db_errors_total": self.db.error_count,
        }


def demo_fault_scenario():
    """
    Demonstrate different fault scenarios and their effects.

    Scenario flow:
    1. Normal operation (no fault)
    2. Database timeout fault (ERROR → FAILURE mitigation)
    3. Database down fault (ERROR → FAILURE mitigation)
    """

    print("=" * 70)
    print("Day10 SlowDatabase Demonstration: Fault → Error → Failure")
    print("=" * 70)

    # Scenario 1: Normal operation (no fault)
    print("\n[Scenario 1] Normal operation (no fault)")
    print("-" * 70)
    normal_db = SlowDatabase(timeout_seconds=2.0)
    workflow = AskWorkflow(normal_db, timeout_seconds=5.0)
    result = workflow.ask("When do I need travel approval?", policy_id="TRAVEL-2025")
    print(f"Result: {result['status']}")
    print(f"Answer: {result['answer']}")
    print(f"Metrics: {workflow.metrics_summary()}")

    # Scenario 2: Database timeout (FAULT → ERROR → FAILURE mitigation)
    print("\n[Scenario 2] Database timeout (FAULT: timeout too short)")
    print("-" * 70)
    timeout_db = SlowDatabase(timeout_seconds=0.1, fail_mode="timeout")
    workflow2 = AskWorkflow(timeout_db, timeout_seconds=5.0)
    result2 = workflow2.ask("When do I need travel approval?", policy_id="TRAVEL-2025")
    print(f"Result: {result2['status']}")
    print(f"Message: {result2.get('message', 'N/A')}")
    print(f"Error Class: {result2.get('error_class', 'N/A')}")
    print(f"Metrics: {workflow2.metrics_summary()}")
    print("\nObservability:")
    print(f"  - User FAILURE: Received 'degraded' message instead of answer")
    print(f"  - System ERROR: Database latency exceeded timeout")
    print(f"  - FAULT: Database client timeout configured too short (0.1s)")
    print(f"  - MITIGATION ACTION: Explicit degradation prevents silent failure")

    # Scenario 3: Database not found (FAULT → ERROR)
    print("\n[Scenario 3] Database not found (FAULT: missing data)")
    print("-" * 70)
    missing_db = SlowDatabase(timeout_seconds=2.0, fail_mode="not_found")
    workflow3 = AskWorkflow(missing_db, timeout_seconds=5.0)
    result3 = workflow3.ask("When do I need travel approval?", policy_id="NONEXISTENT")
    print(f"Result: {result3['status']}")
    print(f"Message: {result3.get('message', 'N/A')}")
    print(f"Error Class: {result3.get('error_class', 'N/A')}")
    print(f"Metrics: {workflow3.metrics_summary()}")
    print("\nObservability:")
    print(f"  - User FAILURE: Received 'degraded' message; cannot answer question")
    print(f"  - System ERROR: Database returned 'not found' for policy ID")
    print(f"  - FAULT: Policy data missing or policy ID incorrect")
    print(f"  - MITIGATION ACTION: Graceful degradation + explicit error signal")

    # Scenario 4: Database unavailable (FAULT → ERROR)
    print("\n[Scenario 4] Database unavailable (FAULT: dependency down)")
    print("-" * 70)
    unavail_db = SlowDatabase(timeout_seconds=2.0, fail_mode="unavailable")
    workflow4 = AskWorkflow(unavail_db, timeout_seconds=5.0)
    result4 = workflow4.ask("When do I need travel approval?", policy_id="TRAVEL-2025")
    print(f"Result: {result4['status']}")
    print(f"Message: {result4.get('message', 'N/A')}")
    print(f"Error Class: {result4.get('error_class', 'N/A')}")
    print(f"Metrics: {workflow4.metrics_summary()}")
    print("\nObservability:")
    print(f"  - User FAILURE: Received 'degraded' message; service unavailable")
    print(f"  - System ERROR: Cannot establish database connection")
    print(f"  - FAULT: Database server is down/unreachable")
    print(f"  - REMEDIATION ACTION: Check database service health; escalate to DB team")

    print("\n" + "=" * 70)
    print("Summary: Handling errors prevents user failures")
    print("=" * 70)
    print("\nKey lessons:")
    print("1. FAULT (timeout config, missing data, down service) is preventable/fixable")
    print("2. ERROR (timeout occurs, query fails, connection refused) is observable")
    print("3. FAILURE (user gets no answer) is what matters to users")
    print("4. Between ERROR and FAILURE, we have a chance to mitigate (graceful degrade)")


if __name__ == "__main__":
    demo_fault_scenario()
