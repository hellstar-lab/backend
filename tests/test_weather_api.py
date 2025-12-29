"""
Weather API Tests
Unit tests for weather endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]

# Note: More comprehensive tests would require mocking Firestore and Auth
