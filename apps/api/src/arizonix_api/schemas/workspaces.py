from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from arizonix_api.db.models.memberships import WorkspaceRole


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("workspace name must contain at least 2 characters")
        return normalized


class WorkspaceUpdate(WorkspaceCreate):
    pass


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    role: WorkspaceRole
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class WorkspacePage(BaseModel):
    items: list[WorkspaceResponse]
    limit: int
    offset: int
    has_more: bool
