"""Human decisions bound to a specific artifact version."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from arizonix_api.domain.common import AwareDatetime, CompanyOwnedRecord


class ReviewScope(StrEnum):
    RESEARCH = "research"
    OUTBOUND_MESSAGE = "outbound_message"


class ReviewArtifactType(StrEnum):
    RESEARCH_PROJECT = "research_project"
    RESEARCH_RUN = "research_run"
    CLAIM = "claim"
    OUTBOUND_MESSAGE = "outbound_message"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class HumanReviewDecision(CompanyOwnedRecord):
    review_scope: ReviewScope
    artifact_type: ReviewArtifactType
    artifact_id: UUID
    artifact_version: int = Field(ge=1)
    actor_id: UUID
    decision: ReviewDecision
    decided_at: AwareDatetime
    explanation: str | None = Field(default=None, min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_scope(self) -> "HumanReviewDecision":
        is_outbound_artifact = self.artifact_type is ReviewArtifactType.OUTBOUND_MESSAGE
        if (self.review_scope is ReviewScope.OUTBOUND_MESSAGE) != is_outbound_artifact:
            raise ValueError("review_scope must match the artifact type")
        return self
