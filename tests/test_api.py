from fastapi.testclient import TestClient

from app.api import api


def test_health_endpoint():
    client = TestClient(api)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

