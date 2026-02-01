"""Tests for agent endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestAgentEndpoint:
    """Tests for the /api/agent/chat endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_chat_endpoint_exists(self, client):
        """Test that the chat endpoint exists and accepts POST."""
        # We can't test the full streaming without API keys,
        # but we can verify the endpoint is registered
        response = client.post(
            "/api/agent/chat",
            json={
                "message": "Hello",
                "session_id": "test-123",
            },
        )
        # Will fail with API key error, but proves endpoint exists
        # and request validation works
        assert response.status_code in [200, 500]

    def test_chat_request_validation(self, client):
        """Test request validation."""
        # Missing required fields
        response = client.post(
            "/api/agent/chat",
            json={},
        )
        assert response.status_code == 422

        # Missing session_id
        response = client.post(
            "/api/agent/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 422

        # Missing message
        response = client.post(
            "/api/agent/chat",
            json={"session_id": "test-123"},
        )
        assert response.status_code == 422

    def test_ideas_endpoint_exists(self, client):
        """Test that the ideas endpoint exists and accepts POST."""
        response = client.post(
            "/api/agent/ideas",
            json={"session_id": "test-123"},
        )
        # Will fail with API key error, but proves endpoint exists
        assert response.status_code in [200, 500, 504]

    def test_visualize_endpoint_exists(self, client):
        """Test that the visualize endpoint exists and accepts POST."""
        response = client.post(
            "/api/agent/visualize",
            json={
                "session_id": "test-123",
                "idea": {"id": "test", "title": "Test Viz", "spec": {}},
            },
        )
        # Will fail with API key error, but proves endpoint exists
        assert response.status_code in [200, 500, 504]


class TestAgentState:
    """Tests for agent state schema."""

    def test_agent_state_schema(self):
        """Test AgentState TypedDict structure."""
        from app.agent.nodes import AgentState

        # Verify it's a TypedDict with expected keys
        assert "messages" in AgentState.__annotations__
        assert "viz_messages" in AgentState.__annotations__
        assert "message_type" in AgentState.__annotations__
        assert "selected_idea" in AgentState.__annotations__
