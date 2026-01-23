"""
Test health endpoints.
Minimal tests that verify endpoints return 200 status.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test GET / endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    # Basic structure check
    assert isinstance(data, dict)
    assert "status" in data or "name" in data  # Accept multiple formats


def test_health_endpoint():
    """Test GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data  # Should have status field


def test_status_endpoint():
    """Test GET /status endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # Should have services information
    assert "services" in data or "status" in data