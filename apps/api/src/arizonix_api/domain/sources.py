"""Source identity and immutable capture contracts."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from arizonix_api.domain.common import AwareDatetime, CompanyOwnedRecord


class SourceKind(StrEnum):
    OFFICIAL_WEBSITE = "official_website"
    REVIEW_PLATFORM = "review_platform"
    NEWS = "news"
    SOCIAL = "social"
    BUSINESS_DIRECTORY = "business_directory"
    OTHER = "other"


class CaptureStatus(StrEnum):
    SUCCESS = "success"
    INACCESSIBLE = "inaccessible"
    FAILED = "failed"


class PublicationPrecision(StrEnum):
    UNKNOWN = "unknown"
    EXACT_TIMESTAMP = "exact_timestamp"
    EXACT_DATE = "exact_date"
    APPROXIMATE_PERIOD = "approximate_period"


class Source(CompanyOwnedRecord):
    kind: SourceKind
    canonical_url: HttpUrl
    title: str | None = Field(default=None, min_length=1, max_length=500)
    identity_fingerprint: str | None = Field(default=None, min_length=1, max_length=500)
    created_at: AwareDatetime


class SourceSnapshot(CompanyOwnedRecord):
    source_id: UUID
    requested_url: HttpUrl
    final_url: HttpUrl | None = None
    capture_status: CaptureStatus
    http_status: int | None = Field(default=None, ge=100, le=599)
    captured_at: AwareDatetime
    content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    storage_reference: str | None = Field(default=None, min_length=1, max_length=1000)
    publication_precision: PublicationPrecision = PublicationPrecision.UNKNOWN
    published_at: AwareDatetime | None = None
    publication_date: date | None = None
    publication_period: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_capture_and_publication(self) -> "SourceSnapshot":
        has_material = self.content_sha256 is not None or self.storage_reference is not None
        if self.capture_status is CaptureStatus.SUCCESS:
            if self.content_sha256 is None or self.storage_reference is None:
                raise ValueError(
                    "a successful capture requires content_sha256 and storage_reference"
                )
        elif has_material:
            raise ValueError("an inaccessible or failed capture must not contain captured material")

        publication_values = (
            self.published_at is not None,
            self.publication_date is not None,
            self.publication_period is not None,
        )
        expected = {
            PublicationPrecision.UNKNOWN: (False, False, False),
            PublicationPrecision.EXACT_TIMESTAMP: (True, False, False),
            PublicationPrecision.EXACT_DATE: (False, True, False),
            PublicationPrecision.APPROXIMATE_PERIOD: (False, False, True),
        }[self.publication_precision]
        if publication_values != expected:
            raise ValueError(
                "publication value must match publication_precision; "
                "capture time is not publication time"
            )
        return self
