"""Tests for policy API timeout handling.

This test demonstrates how a dependency timeout is converted
into an explicit 503 response with a Retry-After header,
allowing the client to determine retry logic.
"""
from fastapi.testclient import TestClient

from app.main import app, get_policy_store, get_timeout_store


client = TestClient(app)


def test_timeout_becomes_explicit_temporary_unavailable() -> None:
    """Test that a timeout in fetch_policy becomes an explicit 503 response.

    Given: The policy store raises TimeoutError
    When: A client requests /policy/{policy_id}
    Then: The response is 503 Service Unavailable with:
      - explicit error code "temporary_unavailable"
      - a request_id for tracing
      - a Retry-After header indicating when to retry
    """
    app.dependency_overrides[get_policy_store] = get_timeout_store

    try:
        response = client.get("/policy/remote-work")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["detail"]["error"] == "temporary_unavailable"
    assert "request_id" in response.json()["detail"]


def test_normal_policy_fetch() -> None:
    """Test that a successful fetch returns the policy.

    Given: The policy store returns a valid policy
    When: A client requests /policy/{policy_id}
    Then: The response is 200 OK with the policy data
    """
    response = client.get("/policy/remote-work")

    assert response.status_code == 200
    assert response.json()["policy_id"] == "remote-work"
    assert "summary" in response.json()
