from fastapi.testclient import TestClient

from arizonix_api.config import Settings
from arizonix_api.main import create_app


def test_health_returns_liveness_contract() -> None:
    settings = Settings(
        _env_file=None,
        app_environment="test",
        app_version="0.1.0",
        log_level="info",
        allowed_origins=["http://frontend.test"],
    )
    client = TestClient(create_app(settings))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "arizonix-api",
        "version": "0.1.0",
    }
