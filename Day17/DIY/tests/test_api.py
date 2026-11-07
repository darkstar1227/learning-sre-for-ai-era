"""Test FastAPI /ask endpoint and event recording."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, event_log


@pytest.fixture(autouse=True)
def clear_events():
    """Clear event log before each test."""
    event_log.clear()
    yield
    event_log.clear()


client = TestClient(app)


class TestHealthEndpoint:
    """Test health check."""

    def test_healthz(self):
        """Health check should return ok."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAskEndpoint:
    """Test /ask endpoint."""

    def test_ask_normal_case(self):
        """Normal question should return answer."""
        response = client.post("/ask", json={"question": "What is SLO?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "SLO" in data["answer"] or "question" in data["answer"].lower()

    def test_ask_records_event_good(self):
        """Normal case should record 'good' event."""
        client.post("/ask", json={"question": "What is SLO?"})
        assert len(event_log) == 1
        event = event_log[0]
        assert event["route"] == "/ask"
        assert event["status"] == "good"
        assert event["latency_ms"] >= 0  # May be 0 on very fast machines

    def test_ask_timeout_scenario(self):
        """Question containing 'timeout' should return 504."""
        response = client.post("/ask", json={"question": "This is timeout"})
        assert response.status_code == 504

    def test_ask_records_event_timeout(self):
        """Timeout case should record timeout event."""
        client.post("/ask", json={"question": "This is timeout"})
        assert len(event_log) == 1
        event = event_log[0]
        assert event["status"] == "timeout"
        assert event["dependency_outcome"]["status"] == "timeout"

    def test_ask_error_scenario(self):
        """Question containing 'error' should return 502."""
        response = client.post("/ask", json={"question": "This is error"})
        assert response.status_code == 502

    def test_ask_records_event_error(self):
        """Error case should record error event."""
        client.post("/ask", json={"question": "This is error"})
        assert len(event_log) == 1
        event = event_log[0]
        assert event["status"] == "error"
        assert event["dependency_outcome"]["status"] == "error"

    def test_ask_empty_question_invalid(self):
        """Empty question should be rejected."""
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422  # Pydantic validation error

    def test_ask_missing_question_invalid(self):
        """Missing question should be rejected."""
        response = client.post("/ask", json={})
        assert response.status_code == 422


class TestEventRecording:
    """Test event recording and retrieval."""

    def test_events_endpoint(self):
        """Events endpoint should return recorded events."""
        client.post("/ask", json={"question": "Q1"})
        client.post("/ask", json={"question": "Q2"})

        response = client.get("/events")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["events"]) == 2

    def test_events_limit_parameter(self):
        """Events endpoint should respect limit parameter."""
        for i in range(10):
            client.post("/ask", json={"question": f"Q{i}"})

        response = client.get("/events?limit=5")
        data = response.json()
        assert len(data["events"]) == 5
        assert data["count"] == 10

    def test_reset_events(self):
        """Reset endpoint should clear event log."""
        client.post("/ask", json={"question": "Q1"})
        assert len(event_log) == 1

        response = client.post("/events/reset")
        assert response.status_code == 200
        assert response.json() == {"status": "reset"}
        assert len(event_log) == 0

    def test_event_schema_no_question(self):
        """Event should not contain the question."""
        client.post("/ask", json={"question": "My secret prompt"})

        event = event_log[0]
        # Event should have these fields
        assert "route" in event
        assert "status" in event
        assert "latency_ms" in event
        # But NOT the question itself
        assert "question" not in event
        assert "My secret" not in str(event)

    def test_event_has_dependency_info(self):
        """Event should include dependency outcome details."""
        client.post("/ask", json={"question": "Q1"})

        event = event_log[0]
        assert "dependency" in event
        assert event["dependency"] == "llm_provider"
        assert "dependency_outcome" in event
        assert "provider" in event["dependency_outcome"]
        assert "status" in event["dependency_outcome"]
        assert "latency_ms" in event["dependency_outcome"]
