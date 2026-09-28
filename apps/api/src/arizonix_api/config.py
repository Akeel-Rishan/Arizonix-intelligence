import json
from enum import StrEnum
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from arizonix_api import __version__


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def _normalize_origin(origin: str) -> str:
    value = origin.strip()
    if not value:
        raise ValueError("CORS origins must not be empty")
    if value == "*":
        raise ValueError("wildcard CORS origins are not allowed")

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"CORS origin must be an absolute HTTP(S) origin: {value!r}")
    if parsed.username or parsed.password:
        raise ValueError(f"CORS origin must not contain credentials: {value!r}")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(f"CORS origin must not contain a path, query, or fragment: {value!r}")
    try:
        _ = parsed.port
    except ValueError as error:
        raise ValueError(f"CORS origin contains an invalid port: {value!r}") from error
    return f"{parsed.scheme}://{parsed.netloc}"


class Settings(BaseSettings):
    """Server-only configuration loaded from ARIZONIX-prefixed environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ARIZONIX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_environment: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_version: str = __version__
    log_level: LogLevel = LogLevel.INFO
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://127.0.0.1:3000", "http://localhost:3000"]
    )
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_cache_seconds: int = Field(default=600, ge=1, le=86_400)
    supabase_jwks_refresh_cooldown_seconds: int = Field(default=30, ge=1, le=3_600)
    supabase_http_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    supabase_jwt_clock_skew_seconds: int = Field(default=30, ge=0, le=300)

    @field_validator("app_version")
    @classmethod
    def validate_app_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("application version must not be empty")
        return normalized

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith("["):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "allowed origins must be comma-separated or a JSON array"
                ) from error
            if not isinstance(decoded, list):
                raise ValueError("allowed origins JSON value must be an array")
            return decoded
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one allowed CORS origin is required")
        normalized = [_normalize_origin(origin) for origin in value]
        return list(dict.fromkeys(normalized))

    @field_validator("supabase_url", mode="before")
    @classmethod
    def normalize_supabase_url(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if not isinstance(value, str):
            return value
        try:
            return _normalize_origin(value)
        except ValueError as error:
            raise ValueError(str(error).replace("CORS origin", "Supabase URL")) from error

    @field_validator("supabase_jwt_audience")
    @classmethod
    def validate_supabase_jwt_audience(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Supabase JWT audience must not be empty")
        return normalized

    @property
    def supabase_jwt_issuer(self) -> str | None:
        if self.supabase_url is None:
            return None
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str | None:
        issuer = self.supabase_jwt_issuer
        if issuer is None:
            return None
        return f"{issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
