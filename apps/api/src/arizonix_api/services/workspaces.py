from uuid import UUID

from sqlalchemy import Select, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from arizonix_api.authorization.permissions import can_rename
from arizonix_api.db.models.memberships import Membership, WorkspaceRole
from arizonix_api.db.models.workspaces import Workspace
from arizonix_api.schemas.workspaces import WorkspaceResponse
from arizonix_api.services.errors import (
    PermissionDenied,
    WorkspaceNotFound,
    translate_database_error,
)


def _workspace_query() -> Select[tuple[Workspace, WorkspaceRole]]:
    return (
        select(Workspace, Membership.role)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == text("arizonix.current_user_id()"))
    )


def _as_response(row: tuple[Workspace, WorkspaceRole]) -> WorkspaceResponse:
    workspace, role = row
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        role=role,
        created_by=workspace.created_by,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


async def list_workspaces(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[WorkspaceResponse], bool]:
    result = await session.execute(
        _workspace_query()
        .order_by(Workspace.created_at, Workspace.id)
        .limit(limit + 1)
        .offset(offset)
    )
    rows = result.all()
    return [_as_response(row) for row in rows[:limit]], len(rows) > limit


async def get_workspace(session: AsyncSession, workspace_id: UUID) -> WorkspaceResponse:
    result = await session.execute(_workspace_query().where(Workspace.id == workspace_id).limit(1))
    row = result.one_or_none()
    if row is None:
        raise WorkspaceNotFound
    return _as_response(row)


async def create_workspace(session: AsyncSession, name: str) -> WorkspaceResponse:
    try:
        workspace_id = await session.scalar(
            text("SELECT arizonix.create_workspace(:name)"), {"name": name}
        )
    except DBAPIError as error:
        translate_database_error(error)
    return await get_workspace(session, workspace_id)


async def rename_workspace(
    session: AsyncSession, workspace_id: UUID, name: str
) -> WorkspaceResponse:
    current = await get_workspace(session, workspace_id)
    if not can_rename(current.role):
        raise PermissionDenied
    try:
        await session.execute(
            text("SELECT arizonix.rename_workspace(:workspace_id, :name)"),
            {"workspace_id": workspace_id, "name": name},
        )
    except DBAPIError as error:
        translate_database_error(error)
    return await get_workspace(session, workspace_id)
