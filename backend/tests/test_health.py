"""Tests del endpoint de health check."""
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthCheck:
    def test_health_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"

    def test_health_returns_json(self):
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
