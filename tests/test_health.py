"""Smoke tests for health endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["phase"].startswith("phase-")
