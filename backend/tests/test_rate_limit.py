"""Tests del rate limiting."""
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app, raise_server_exceptions=False)


class TestRateLimit:
    def test_login_rate_limit_triggers(self):
        for _ in range(20):
            client.post("/api/auth/login", json={"username": "test", "password": "wrong"})
        r = client.post("/api/auth/login", json={"username": "test", "password": "wrong"})
        assert r.status_code == 429

    def test_rate_limit_returns_message(self):
        for _ in range(20):
            client.post("/api/auth/login", json={"username": "test", "password": "wrong"})
        r = client.post("/api/auth/login", json={"username": "test", "password": "wrong"})
        assert r.status_code == 429
        body = r.json()
        assert "error" in body
        assert "rate limit" in body["error"].lower()

    def test_health_not_rate_limited(self):
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
