from fastapi.testclient import TestClient

from arizonix_api.config import Settings
from arizonix_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(allowed_origins=["http://frontend.test"])))


def test_allowed_origin_receives_cors_header() -> None:
    response = make_client().get("/api/v1/health", headers={"Origin": "http://frontend.test"})
    assert response.headers["access-control-allow-origin"] == "http://frontend.test"


def test_disallowed_origin_is_not_granted_access() -> None:
    response = make_client().get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers
