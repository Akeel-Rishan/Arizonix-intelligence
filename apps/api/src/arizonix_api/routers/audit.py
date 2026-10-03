from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from arizonix_api.audit.schemas import AuditEventPage, AuditEventResponse
from arizonix_api.authorization.dependencies import AuthenticatedSession
from arizonix_api.db.models.audit import AuditAction
from arizonix_api.services import audit

router = APIRouter(prefix="/workspaces/{workspace_id}/audit-events", tags=["workspace audit"])
PageLimit = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=AuditEventPage)
async def list_audit_events(
    workspace_id: UUID,
    session: AuthenticatedSession,
    response: Response,
    limit: PageLimit = 25,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    action: AuditAction | None = None,
    actor_user_id: UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> AuditEventPage:
    response.headers["Cache-Control"] = "private, no-store"
    return await audit.list_audit_events(
        session,
        workspace_id,
        limit=limit,
        cursor=cursor,
        action=action,
        actor_user_id=actor_user_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )


@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    workspace_id: UUID, event_id: UUID, session: AuthenticatedSession, response: Response
) -> AuditEventResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await audit.get_audit_event(session, workspace_id, event_id)
