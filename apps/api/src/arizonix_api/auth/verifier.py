import asyncio
import time
from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

import httpx
import jwt
from jwt import PyJWK

from arizonix_api.auth.principal import Principal
from arizonix_api.config import Settings

ALLOWED_ALGORITHMS = frozenset({"RS256", "ES256"})
MAX_TOKEN_LENGTH = 16_384


class InvalidAccessToken(Exception):
    """The caller supplied a token that cannot be trusted."""


class AuthenticationServiceUnavailable(Exception):
    """The signing-key service could not establish token trust."""


class AccessTokenVerifier(Protocol):
    async def verify(self, token: str) -> Principal: ...


class UnavailableTokenVerifier:
    async def verify(self, token: str) -> Principal:
        del token
        raise AuthenticationServiceUnavailable("Supabase authentication is not configured")


class JwksProvider:
    """Small bounded JWKS cache with guarded refreshes for signing-key rotation."""

    def __init__(
        self,
        jwks_url: str,
        *,
        cache_seconds: int,
        refresh_cooldown_seconds: int,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._jwks_url = jwks_url
        self._cache_seconds = cache_seconds
        self._refresh_cooldown_seconds = refresh_cooldown_seconds
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._keys: dict[str, PyJWK] = {}
        self._expires_at = 0.0
        self._last_forced_refresh_at = float("-inf")
        self._refresh_unavailable_until = 0.0
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> PyJWK:
        now = time.monotonic()
        cached = self._keys.get(kid)
        if cached is not None and now < self._expires_at:
            return cached

        async with self._lock:
            now = time.monotonic()
            cached = self._keys.get(kid)
            if cached is not None and now < self._expires_at:
                return cached

            should_refresh = not self._keys or now >= self._expires_at
            cooldown_elapsed = now - self._last_forced_refresh_at >= self._refresh_cooldown_seconds
            if not should_refresh and cooldown_elapsed:
                should_refresh = True
                self._last_forced_refresh_at = now

            if should_refresh:
                try:
                    await self._refresh()
                except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError) as error:
                    self._last_forced_refresh_at = now
                    self._refresh_unavailable_until = now + self._refresh_cooldown_seconds
                    self._expires_at = max(self._expires_at, self._refresh_unavailable_until)
                    stale = self._keys.get(kid)
                    if stale is not None:
                        return stale
                    raise AuthenticationServiceUnavailable(
                        "Unable to retrieve signing keys"
                    ) from error

            key = self._keys.get(kid)
            if key is None:
                if time.monotonic() < self._refresh_unavailable_until:
                    raise AuthenticationServiceUnavailable("Unable to retrieve signing keys")
                raise InvalidAccessToken("Unknown signing key")
            return key

    async def _refresh(self) -> None:
        if self._client is None:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
                response = await client.get(self._jwks_url)
        else:
            response = await self._client.get(
                self._jwks_url,
                timeout=self._timeout,
                follow_redirects=False,
            )
        response.raise_for_status()
        payload = response.json()
        raw_keys = payload["keys"]
        if not isinstance(raw_keys, list):
            raise ValueError("JWKS keys must be an array")

        parsed: dict[str, PyJWK] = {}
        for raw_key in raw_keys:
            if not isinstance(raw_key, Mapping):
                continue
            kid = raw_key.get("kid")
            algorithm = raw_key.get("alg")
            if isinstance(kid, str) and kid and algorithm in ALLOWED_ALGORITHMS:
                parsed[kid] = PyJWK.from_dict(dict(raw_key), algorithm=algorithm)
        if not parsed:
            raise ValueError("JWKS did not contain a supported signing key")
        self._keys = parsed
        self._expires_at = time.monotonic() + self._cache_seconds
        self._refresh_unavailable_until = 0.0


class SupabaseTokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks: JwksProvider,
        clock_skew_seconds: int,
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._jwks = jwks
        self._clock_skew_seconds = clock_skew_seconds

    async def verify(self, token: str) -> Principal:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            raise InvalidAccessToken("Malformed access token")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise InvalidAccessToken("Malformed access token") from error

        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in ALLOWED_ALGORITHMS or not isinstance(kid, str) or not kid:
            raise InvalidAccessToken("Unsupported access token")

        key = await self._jwks.get_key(kid)
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key.key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._clock_skew_seconds,
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as error:
            raise InvalidAccessToken("Invalid access token") from error

        try:
            user_id = UUID(claims["sub"])
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidAccessToken("Invalid access token subject") from error
        email = claims.get("email")
        if email is not None and not isinstance(email, str):
            raise InvalidAccessToken("Invalid access token email")
        return Principal(user_id=user_id, email=email)


def build_token_verifier(settings: Settings) -> AccessTokenVerifier:
    issuer = settings.supabase_jwt_issuer
    jwks_url = settings.supabase_jwks_url
    if issuer is None or jwks_url is None:
        return UnavailableTokenVerifier()
    return SupabaseTokenVerifier(
        issuer=issuer,
        audience=settings.supabase_jwt_audience,
        jwks=JwksProvider(
            jwks_url,
            cache_seconds=settings.supabase_jwks_cache_seconds,
            refresh_cooldown_seconds=settings.supabase_jwks_refresh_cooldown_seconds,
            timeout_seconds=settings.supabase_http_timeout_seconds,
        ),
        clock_skew_seconds=settings.supabase_jwt_clock_skew_seconds,
    )
