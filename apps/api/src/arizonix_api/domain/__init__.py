"""Versioned core domain contracts with no framework, database, or provider dependency."""

from arizonix_api.domain.claims import (
    Claim,
    ClaimEvidenceRelationship,
    ClaimLifecycleStatus,
    EvidenceRelationshipKind,
    EvidentiaryClassification,
)
from arizonix_api.domain.common import CONTRACT_VERSION
from arizonix_api.domain.companies import Company
from arizonix_api.domain.evidence import (
    Evidence,
    EvidenceStrength,
    EvidenceType,
    ExactExcerptLocator,
    Freshness,
)
from arizonix_api.domain.research import (
    ProjectProgression,
    ResearchOutcome,
    ResearchProject,
    ResearchRun,
    RunStatus,
)
from arizonix_api.domain.reviews import (
    HumanReviewDecision,
    ReviewArtifactType,
    ReviewDecision,
    ReviewScope,
)
from arizonix_api.domain.sources import (
    CaptureStatus,
    PublicationPrecision,
    Source,
    SourceKind,
    SourceSnapshot,
)
from arizonix_api.domain.validation import (
    DomainBundle,
    DomainIntegrityError,
    validate_domain_bundle,
)

__all__ = [
    "CONTRACT_VERSION",
    "CaptureStatus",
    "Claim",
    "ClaimEvidenceRelationship",
    "ClaimLifecycleStatus",
    "Company",
    "DomainBundle",
    "DomainIntegrityError",
    "Evidence",
    "EvidenceRelationshipKind",
    "EvidenceStrength",
    "EvidenceType",
    "EvidentiaryClassification",
    "ExactExcerptLocator",
    "Freshness",
    "HumanReviewDecision",
    "ProjectProgression",
    "PublicationPrecision",
    "ResearchOutcome",
    "ResearchProject",
    "ResearchRun",
    "ReviewArtifactType",
    "ReviewDecision",
    "ReviewScope",
    "RunStatus",
    "Source",
    "SourceKind",
    "SourceSnapshot",
    "validate_domain_bundle",
]
