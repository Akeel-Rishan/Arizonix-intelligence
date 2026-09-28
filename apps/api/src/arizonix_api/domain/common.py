"""Shared primitives for framework-independent domain contracts."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0"


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")
    return value


AwareDatetime = Annotated[datetime, AfterValidator(_require_timezone)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class ContractModel(BaseModel):
    """Base model for strict, forward-compatible contract parsing."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WorkspaceRecord(ContractModel):
    id: UUID
    workspace_id: UUID


class CompanyOwnedRecord(WorkspaceRecord):
    company_id: UUID
