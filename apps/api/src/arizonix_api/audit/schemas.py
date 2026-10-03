from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from arizonix_api.db.models.audit import AuditAction


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    actor_user_id: UUID
    action: AuditAction
    target_type: str
    target_id: UUID
    occurred_at: datetime
    request_id: UUID
    event_schema_version: int
    details: dict[str, Any]


class AuditEventPage(BaseModel):
    items: list[AuditEventResponse]
    next_cursor: str | None
