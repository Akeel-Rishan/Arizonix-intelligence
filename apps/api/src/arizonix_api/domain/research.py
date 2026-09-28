"""Research project progression and run-execution contracts."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from arizonix_api.domain.common import AwareDatetime, CompanyOwnedRecord


class ProjectProgression(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    CLOSED = "closed"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchOutcome(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_MEANINGFUL_PROBLEM = "no_meaningful_problem"
    UNSUITABLE_BUSINESS = "unsuitable_business"
    STALE_DATA = "stale_data"
    OPPORTUNITY_CANDIDATE = "opportunity_candidate"
    HUMAN_REJECTED = "human_rejected"


class ResearchProject(CompanyOwnedRecord):
    objective: str = Field(min_length=1, max_length=2000)
    version: int = Field(ge=1)
    progression: ProjectProgression
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_dates(self) -> "ResearchProject":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be before created_at")
        return self


class ResearchRun(CompanyOwnedRecord):
    project_id: UUID
    status: RunStatus
    queued_at: AwareDatetime
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    outcome: ResearchOutcome | None = None

    @model_validator(mode="after")
    def validate_execution_dates_and_outcome(self) -> "ResearchRun":
        if self.started_at is not None and self.started_at < self.queued_at:
            raise ValueError("started_at must not be before queued_at")
        if self.completed_at is not None:
            baseline = self.started_at or self.queued_at
            if self.completed_at < baseline:
                raise ValueError("completed_at must not be before run start")
        if self.status is RunStatus.SUCCEEDED:
            if self.completed_at is None:
                raise ValueError("a succeeded run requires completed_at")
            if self.outcome is None:
                raise ValueError("a succeeded run requires a research outcome")
        elif self.outcome is not None:
            raise ValueError("only a succeeded run may record a research outcome")
        return self
