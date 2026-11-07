"""Policy API service for Day10 DIY: Fault-Error-Failure analysis.

This module demonstrates how to handle dependency timeouts explicitly,
converting them into a clear service contract response rather than
internal errors.
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Protocol
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException


logger = logging.getLogger("policy-api")
app = FastAPI()


class PolicyStore(Protocol):
    """Protocol for policy store implementations."""

    def fetch_policy(self, policy_id: str) -> dict[str, str]:
        """Return one policy record or raise a dependency exception."""


class InMemoryPolicyStore:
    """In-memory policy store that always succeeds."""

    def fetch_policy(self, policy_id: str) -> dict[str, str]:
        return {
            "policy_id": policy_id,
            "summary": "Remote work requires manager approval.",
        }


class TimeoutPolicyStore:
    """Fake policy store that simulates a timeout."""

    def fetch_policy(self, policy_id: str) -> dict[str, str]:
        raise TimeoutError("simulated policy-store timeout")


def get_policy_store() -> PolicyStore:
    """Default dependency: return in-memory store."""
    return InMemoryPolicyStore()


def get_timeout_store() -> PolicyStore:
    """Test dependency: return timeout-simulating store."""
    return TimeoutPolicyStore()


@app.get("/policy/{policy_id}")
def read_policy(
    policy_id: str,
    store: Annotated[PolicyStore, Depends(get_policy_store)],
) -> dict[str, str]:
    """Fetch a policy and handle dependency timeouts explicitly.

    When the policy store times out, return 503 with a clear error code
    and Retry-After header, allowing the client to decide when to retry.
    """
    request_id = str(uuid4())

    try:
        policy = store.fetch_policy(policy_id)
    except TimeoutError:
        logger.warning(
            json.dumps(
                {
                    "event": "policy_lookup_failed",
                    "request_id": request_id,
                    "dependency": "policy-store",
                    "error_class": "dependency_timeout",
                    "user_outcome": "temporary_unavailable",
                    "mitigation": "explicit_503",
                }
            )
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "temporary_unavailable",
                "request_id": request_id,
            },
            headers={"Retry-After": "5"},
        ) from None

    logger.info(
        json.dumps(
            {
                "event": "policy_lookup_succeeded",
                "request_id": request_id,
                "dependency": "policy-store",
                "user_outcome": "policy_returned",
            }
        )
    )
    return policy
