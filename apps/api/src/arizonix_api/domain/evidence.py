"""Inspectable observations derived from captured source material."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from arizonix_api.domain.common import CompanyOwnedRecord, Confidence, ContractModel


class EvidenceType(StrEnum):
    DIRECT_OBSERVATION = "direct_observation"
    EXACT_EXCERPT = "exact_excerpt"
    STRUCTURED_RECORD = "structured_record"
    ATTRIBUTED_STATEMENT = "attributed_statement"


class Freshness(StrEnum):
    UNKNOWN = "unknown"
    CURRENT = "current"
    RECENT = "recent"
    HISTORICAL = "historical"
    STALE = "stale"


class EvidenceStrength(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class ExactExcerptLocator(ContractModel):
    excerpt: str = Field(min_length=1, max_length=10000)
    selector: str | None = Field(default=None, min_length=1, max_length=1000)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> "ExactExcerptLocator":
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("excerpt offsets must either both be provided or both be absent")
        if self.start_offset is not None and self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class Evidence(CompanyOwnedRecord):
    display_label: str = Field(pattern=r"^EV-[0-9]{3,}$")
    source_snapshot_id: UUID
    evidence_type: EvidenceType
    observation: str = Field(min_length=1, max_length=10000)
    excerpt_locator: ExactExcerptLocator | None = None
    freshness: Freshness = Freshness.UNKNOWN
    strength: EvidenceStrength | None = None
    source_reliability: Confidence | None = None

    @model_validator(mode="after")
    def validate_excerpt(self) -> "Evidence":
        if self.evidence_type is EvidenceType.EXACT_EXCERPT and self.excerpt_locator is None:
            raise ValueError("exact_excerpt evidence requires excerpt_locator")
        return self
