import json
import logging

from httpx import ASGITransport, AsyncClient

from arizonix_api.config import Settings
from arizonix_api.main import create_app


async def _missing_auth_request() -> tuple[int, dict[str, str]]:
    app = create_app(Settings(_env_file=None, app_environment="test"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://api.test") as client:
        response = await client.get(
            "/api/v1/me?token=do-not-log",
            headers={"Cookie": "secret=cookie", "X-Attack": "line-one\nline-two"},
        )
    return response.status_code, dict(response.headers)


def test_authentication_failure_log_is_structured_and_redacted(caplog) -> None:  # type: ignore[no-untyped-def]
    import asyncio

    with caplog.at_level(logging.WARNING, logger="arizonix.security"):
        status_code, headers = asyncio.run(_missing_auth_request())

    assert status_code == 401
    request_id = headers["x-request-id"]
    matching = [
        record.message for record in caplog.records if "authentication_failed" in record.message
    ]
    assert len(matching) == 1
    payload = json.loads(matching[0])
    assert payload == {
        "actor_user_id": None,
        "event": "security.authentication_failed",
        "method": "GET",
        "reason": "missing_bearer_token",
        "request_id": request_id,
        "route": "/me",
        "severity": "WARNING",
        "status": 401,
        "timestamp": payload["timestamp"],
    }
    combined = "\n".join(
        record.message for record in caplog.records if record.name == "arizonix.security"
    )
    for secret in ("do-not-log", "secret=cookie", "line-one", "line-two"):
        assert secret not in combined
