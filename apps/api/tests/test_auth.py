import base64
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from arizonix_api.auth.principal import Principal
from arizonix_api.auth.verifier import (
    AuthenticationServiceUnavailable,
    JwksProvider,
    SupabaseTokenVerifier,
)
from arizonix_api.config import Settings
from arizonix_api.main import create_app

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
USER_ID = UUID("1309ec68-70d6-47e8-9dc2-bd9d73177a84")


def encode_integer(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_key(kid: str = "key-1") -> tuple[Any, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    return private_key, {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": encode_integer(numbers.n),
        "e": encode_integer(numbers.e),
    }


def make_token(
    private_key: Any,
    *,
    kid: str = "key-1",
    algorithm: str = "RS256",
    overrides: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(USER_ID),
        "email": "analyst@example.com",
        "aud": AUDIENCE,
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    claims.update(overrides or {})
    return jwt.encode(claims, private_key, algorithm=algorithm, headers={"kid": kid})


def make_verifier(
    jwks: list[dict[str, str]],
    *,
    handler: Callable[[httpx.Request], httpx.Response] | None = None,
    cache_seconds: int = 600,
) -> tuple[SupabaseTokenVerifier, httpx.AsyncClient]:
    transport = httpx.MockTransport(
        handler or (lambda request: httpx.Response(200, json={"keys": jwks}))
    )
    client = httpx.AsyncClient(transport=transport)
    provider = JwksProvider(
        f"{ISSUER}/.well-known/jwks.json",
        cache_seconds=cache_seconds,
        refresh_cooldown_seconds=30,
        timeout_seconds=1,
        client=client,
    )
    return (
        SupabaseTokenVerifier(
            issuer=ISSUER,
            audience=AUDIENCE,
            jwks=provider,
            clock_skew_seconds=0,
        ),
        client,
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_valid_access_token_returns_minimal_principal() -> None:
    private_key, public_jwk = make_key()
    verifier, client = make_verifier([public_jwk])
    try:
        principal = await verifier.verify(make_token(private_key))
    finally:
        await client.aclose()

    assert principal == Principal(user_id=USER_ID, email="analyst@example.com")


class StubVerifier:
    def __init__(self, principal: Principal | None = None) -> None:
        self.principal = principal or Principal(user_id=USER_ID, email="analyst@example.com")

    async def verify(self, token: str) -> Principal:
        assert token == "valid-token"
        return self.principal


def make_test_settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        app_environment="test",
        app_version="0.1.0",
        allowed_origins=["http://frontend.test"],
        **overrides,
    )


def test_me_requires_bearer_auth_and_returns_exact_contract() -> None:
    client = TestClient(create_app(make_test_settings(), token_verifier=StubVerifier()))

    missing = client.get("/api/v1/me")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    wrong_scheme = client.get("/api/v1/me", headers={"Authorization": "Basic credentials"})
    assert wrong_scheme.status_code == 401

    response = client.get("/api/v1/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "user_id": str(USER_ID),
        "email": "analyst@example.com",
    }


def test_unconfigured_auth_is_controlled_and_health_remains_public() -> None:
    client = TestClient(create_app(make_test_settings()))

    assert client.get("/api/v1/health").status_code == 200
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication service unavailable"}


def test_cors_allows_authorization_header_for_configured_origin() -> None:
    client = TestClient(create_app(make_test_settings()))
    response = client.options(
        "/api/v1/me",
        headers={
            "Origin": "http://frontend.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "service_role"},
        {"sub": "not-a-uuid"},
    ],
)
async def test_invalid_claims_are_rejected(overrides: dict[str, Any]) -> None:
    private_key, public_jwk = make_key()
    verifier, client = make_verifier([public_jwk])
    try:
        with pytest.raises(Exception, match="Invalid access token"):
            await verifier.verify(make_token(private_key, overrides=overrides))
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_bad_signature_and_unknown_algorithm_are_rejected() -> None:
    trusted_key, public_jwk = make_key()
    attacker_key, _ = make_key("attacker")
    verifier, client = make_verifier([public_jwk])
    try:
        with pytest.raises(Exception, match="Malformed access token"):
            await verifier.verify("not.a.jwt")
        with pytest.raises(Exception, match="Invalid access token"):
            await verifier.verify(make_token(attacker_key))
        now = int(time.time())
        missing_subject = jwt.encode(
            {
                "aud": AUDIENCE,
                "iss": ISSUER,
                "iat": now,
                "exp": now + 60,
            },
            trusted_key,
            algorithm="RS256",
            headers={"kid": "key-1"},
        )
        with pytest.raises(Exception, match="Invalid access token"):
            await verifier.verify(missing_subject)
        none_token = jwt.encode(
            {"sub": str(USER_ID), "exp": int(time.time()) + 60, "iat": int(time.time())},
            key="",
            algorithm="none",
            headers={"kid": "key-1"},
        )
        with pytest.raises(Exception, match="Unsupported access token"):
            await verifier.verify(none_token)
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_key_rotation_refreshes_once_and_unknown_kids_are_bounded() -> None:
    first_private, first_public = make_key("first")
    second_private, second_public = make_key("second")
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        keys = [first_public] if calls == 1 else [first_public, second_public]
        return httpx.Response(200, json={"keys": keys})

    verifier, client = make_verifier([first_public], handler=handler)
    try:
        assert (await verifier.verify(make_token(first_private, kid="first"))).user_id == USER_ID
        assert (await verifier.verify(make_token(second_private, kid="second"))).user_id == USER_ID
        for index in range(5):
            with pytest.raises(Exception, match="Unknown signing key"):
                await verifier.verify(make_token(second_private, kid=f"missing-{index}"))
    finally:
        await client.aclose()

    assert calls == 2


@pytest.mark.anyio
async def test_jwks_outage_uses_known_stale_key_but_fails_closed_for_unknown_key() -> None:
    private_key, public_jwk = make_key()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json={"keys": [public_jwk]})
        raise httpx.ConnectError("offline", request=request)

    verifier, client = make_verifier([public_jwk], handler=handler, cache_seconds=1)
    try:
        token = make_token(private_key)
        await verifier.verify(token)
        verifier._jwks._expires_at = 0  # Simulate TTL expiry without slowing the suite.
        assert (await verifier.verify(token)).user_id == USER_ID
        with pytest.raises(AuthenticationServiceUnavailable):
            await verifier.verify(make_token(private_key, kid="missing"))
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_jwks_outage_without_a_cached_key_is_unavailable() -> None:
    private_key, _ = make_key()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    verifier, client = make_verifier([], handler=handler)
    try:
        with pytest.raises(AuthenticationServiceUnavailable):
            await verifier.verify(make_token(private_key))
    finally:
        await client.aclose()
