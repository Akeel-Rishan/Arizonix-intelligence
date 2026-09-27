from fastapi.testclient import TestClient

from arizonix_api.config import Settings
from arizonix_api.main import create_app


def test_health_returns_liveness_contract() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "arizonix-api",
        "version": "0.1.0",
    }
