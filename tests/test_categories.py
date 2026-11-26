"""Tests for the 15 canonical MVTec AD categories endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_list_categories_returns_all_15() -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 15
    ids = {item["id"] for item in data}
    assert {"bottle", "cable", "carpet", "zipper"}.issubset(ids)


def test_unknown_category_returns_404() -> None:
    response = client.get("/api/v1/categories/unknown_item")
    assert response.status_code == 404
