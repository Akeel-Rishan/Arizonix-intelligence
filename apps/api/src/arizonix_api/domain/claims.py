"""Versioned claim and evidence-link contracts."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from arizonix_api.domain.common import CompanyOwnedRecord, Confidence


class ClaimLifecycleStatus(StrEnum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class EvidentiaryClassification(StrEnum):
    FACT = "fact"
    SIGNAL = "signal"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    HISTORICAL = "historical"
    STALE = "stale"
    INVALID = "invalid"


class EvidenceRelationshipKind(StrEnum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    AMBIGUOUS = "ambiguous"


class Claim(CompanyOwnedRecord):
    research_run_id: UUID | None = None
    statement: str = Field(min_length=1, max_length=10000)
    version: int = Field(ge=1)
    lifecycle_status: ClaimLifecycleStatus
    evidentiary_classification: EvidentiaryClassification
    confidence: Confidence | None = None


class ClaimEvidenceRelationship(CompanyOwnedRecord):
    claim_id: UUID
    claim_version: int = Field(ge=1)
    evidence_id: UUID
    relationship: EvidenceRelationshipKind
    rationale: str | None = Field(default=None, min_length=1, max_length=2000)
