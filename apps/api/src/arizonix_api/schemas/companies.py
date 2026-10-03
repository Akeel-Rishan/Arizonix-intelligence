from datetime import datetime
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ArchiveFilter(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL = "all"


def _trim_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("value must not be blank")
    return normalized


def _trim_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_website(value: str | None) -> str | None:
    value = _trim_optional(value)
    if value is None:
        return None
    if any(character.isspace() for character in value):
        raise ValueError("website URL must not contain whitespace")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("website URL is malformed") from error
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("website URL must use an explicit http or https scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("website URL must not include credentials")
    return value


class CompanyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(max_length=200)]
    website_url: Annotated[str | None, Field(max_length=2048)] = None
    industry: Annotated[str | None, Field(max_length=100)] = None
    country_code: Annotated[str | None, Field(max_length=2)] = None
    description: Annotated[str | None, Field(max_length=2000)] = None
    notes: Annotated[str | None, Field(max_length=5000)] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        return _validate_website(value)

    @field_validator("industry", "description", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _trim_optional(value)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        normalized = _trim_optional(value)
        if normalized is None:
            return None
        normalized = normalized.upper()
        if len(normalized) != 2 or not normalized.isascii() or not normalized.isalpha():
            raise ValueError("country code must be two ASCII letters")
        return normalized


class CompanyCreate(CompanyFields):
    pass


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(ge=1)]
    name: Annotated[str | None, Field(max_length=200)] = None
    website_url: Annotated[str | None, Field(max_length=2048)] = None
    industry: Annotated[str | None, Field(max_length=100)] = None
    country_code: Annotated[str | None, Field(max_length=2)] = None
    description: Annotated[str | None, Field(max_length=2000)] = None
    notes: Annotated[str | None, Field(max_length=5000)] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return _trim_required(value)

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        return _validate_website(value)

    @field_validator("industry", "description", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _trim_optional(value)

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return CompanyFields.normalize_country_code(value)

    @model_validator(mode="after")
    def require_change(self) -> "CompanyUpdate":
        if not (self.model_fields_set - {"expected_version"}):
            raise ValueError("at least one company field is required")
        return self


class CompanyLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: Annotated[int, Field(ge=1)]


class CompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    website_url: str | None
    industry: str | None
    country_code: str | None
    description: str | None
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    archived_by: UUID | None
    version: int


class CompanyResponse(CompanyListItem):
    notes: str | None


class CompanyPage(BaseModel):
    items: list[CompanyListItem]
    next_cursor: str | None
