from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "md-data.org" in response.json()["message"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_catalog() -> None:
    response = client.get("/v1/search")
    assert response.status_code == 200
    assert len(response.json()) >= 1

