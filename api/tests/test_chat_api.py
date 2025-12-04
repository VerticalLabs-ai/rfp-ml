"""Tests for chat API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_chat_session():
    """Test creating a new chat session for an existing RFP."""
    # First, get an existing RFP ID
    response = client.get("/api/v1/rfps/discovered?limit=1")
    assert response.status_code == 200
    rfps = response.json()

    if not isinstance(rfps, list) or len(rfps) == 0:
        pytest.skip("No RFPs in database")

    rfp_id = rfps[0]["rfp_id"]

    # Create session
    response = client.post(f"/api/v1/chat/{rfp_id}/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["rfp_id"] == rfp_id
    assert data["message_count"] == 0


def test_list_chat_sessions():
    """Test listing chat sessions for an RFP."""
    response = client.get("/api/v1/rfps/discovered?limit=1")
    assert response.status_code == 200
    rfps = response.json()

    if not isinstance(rfps, list) or len(rfps) == 0:
        pytest.skip("No RFPs in database")

    rfp_id = rfps[0]["rfp_id"]

    response = client.get(f"/api/v1/chat/{rfp_id}/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert isinstance(data["sessions"], list)


def test_get_chat_suggestions():
    """Test getting suggested questions for an RFP."""
    response = client.get("/api/v1/rfps/discovered?limit=1")
    assert response.status_code == 200
    rfps = response.json()

    if not isinstance(rfps, list) or len(rfps) == 0:
        pytest.skip("No RFPs in database")

    rfp_id = rfps[0]["rfp_id"]

    response = client.get(f"/api/v1/chat/{rfp_id}/chat/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0
    assert isinstance(data["suggestions"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
