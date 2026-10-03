import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from arizonix_api.audit.schemas import AuditEventPage, AuditEventResponse
from arizonix_api.db.models.audit import AuditAction, AuditEvent
from arizonix_api.db.models.memberships import WorkspaceRole
from arizonix_api.services.errors import InvalidAuditQuery, PermissionDenied
from arizonix_api.services.memberships import actor_role

MAX_DATE_RANGE = timedelta(days=366)


def _encode_cursor(event: AuditEvent) -> str:
    payload = json.dumps(
        [event.occurred_at.astimezone(UTC).isoformat(), str(event.id)], separators=(",", ":")
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    if not cursor or len(cursor) > 512:
        raise InvalidAuditQuery
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        value = json.loads(raw)
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError
        occurred_at = datetime.fromisoformat(value[0])
        if occurred_at.tzinfo is None:
            raise ValueError
        return occurred_at, UUID(value[1])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise InvalidAuditQuery from error


async def _authorize(session: AsyncSession, workspace_id: UUID) -> None:
    role = await actor_role(session, workspace_id)
    if role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        raise PermissionDenied


async def list_audit_events(
    session: AsyncSession,
    workspace_id: UUID,
    *,
    limit: int,
    cursor: str | None,
    action: AuditAction | None,
    actor_user_id: UUID | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
) -> AuditEventPage:
    await _authorize(session, workspace_id)
    if (occurred_from is None) != (occurred_to is None):
        raise InvalidAuditQuery
    if occurred_from is not None and occurred_to is not None:
        if occurred_from.tzinfo is None or occurred_to.tzinfo is None:
            raise InvalidAuditQuery
        if occurred_from > occurred_to or occurred_to - occurred_from > MAX_DATE_RANGE:
            raise InvalidAuditQuery

    statement = select(AuditEvent).where(AuditEvent.workspace_id == workspace_id)
    if action is not None:
        statement = statement.where(AuditEvent.action == action)
    if actor_user_id is not None:
        statement = statement.where(AuditEvent.actor_user_id == actor_user_id)
    if occurred_from is not None and occurred_to is not None:
        statement = statement.where(
            AuditEvent.occurred_at >= occurred_from, AuditEvent.occurred_at <= occurred_to
        )
    if cursor is not None:
        cursor_time, cursor_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                AuditEvent.occurred_at < cursor_time,
                and_(AuditEvent.occurred_at == cursor_time, AuditEvent.id < cursor_id),
            )
        )
    result = await session.scalars(
        statement.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).limit(limit + 1)
    )
    rows = list(result)
    page_rows = rows[:limit]
    return AuditEventPage(
        items=[AuditEventResponse.model_validate(event) for event in page_rows],
        next_cursor=_encode_cursor(page_rows[-1]) if len(rows) > limit else None,
    )


async def get_audit_event(
    session: AsyncSession, workspace_id: UUID, event_id: UUID
) -> AuditEventResponse:
    await _authorize(session, workspace_id)
    event = await session.scalar(
        select(AuditEvent).where(AuditEvent.workspace_id == workspace_id, AuditEvent.id == event_id)
    )
    if event is None:
        from arizonix_api.services.errors import AuditEventNotFound

        raise AuditEventNotFound
    return AuditEventResponse.model_validate(event)
