from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from arizonix_api.db.models.memberships import WorkspaceRole


class MemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role: WorkspaceRole


class MemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: WorkspaceRole


class MemberResponse(BaseModel):
    user_id: UUID
    email: str | None
    role: WorkspaceRole
    created_at: datetime
    updated_at: datetime


class MemberPage(BaseModel):
    items: list[MemberResponse]
    limit: int
    offset: int
    has_more: bool


class LeaveResponse(BaseModel):
    left: bool = True
