from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from arizonix_api.authorization.permissions import (
    can_add_member,
    can_change_role,
    can_remove_member,
)
from arizonix_api.db.models.memberships import Membership, WorkspaceRole
from arizonix_api.db.models.users import ApplicationUser
from arizonix_api.schemas.memberships import MemberResponse
from arizonix_api.services.errors import (
    MembershipNotFound,
    PermissionDenied,
    WorkspaceNotFound,
    translate_database_error,
)


async def actor_role(session: AsyncSession, workspace_id: UUID) -> WorkspaceRole:
    role = await session.scalar(
        select(Membership.role).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == text("arizonix.current_user_id()"),
        )
    )
    if role is None:
        raise WorkspaceNotFound
    return role


async def target_role(session: AsyncSession, workspace_id: UUID, user_id: UUID) -> WorkspaceRole:
    role = await session.scalar(
        select(Membership.role).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    )
    if role is None:
        raise MembershipNotFound
    return role


async def list_members(
    session: AsyncSession, workspace_id: UUID, *, limit: int, offset: int
) -> tuple[list[MemberResponse], bool]:
    await actor_role(session, workspace_id)
    result = await session.execute(
        select(Membership, ApplicationUser.email)
        .join(ApplicationUser, ApplicationUser.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
        .order_by(Membership.created_at, Membership.user_id)
        .limit(limit + 1)
        .offset(offset)
    )
    rows = result.all()
    return [
        MemberResponse(
            user_id=membership.user_id,
            email=email,
            role=membership.role,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )
        for membership, email in rows[:limit]
    ], len(rows) > limit


async def add_member(
    session: AsyncSession, workspace_id: UUID, user_id: UUID, role: WorkspaceRole
) -> None:
    current = await actor_role(session, workspace_id)
    if not can_add_member(current, role):
        raise PermissionDenied
    try:
        await session.execute(
            text("SELECT arizonix.add_workspace_member(:workspace_id, :user_id, :role)"),
            {"workspace_id": workspace_id, "user_id": user_id, "role": role.value},
        )
    except DBAPIError as error:
        translate_database_error(error)


async def change_member_role(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID,
    role: WorkspaceRole,
) -> None:
    current = await actor_role(session, workspace_id)
    target = await target_role(session, workspace_id, user_id)
    if not can_change_role(current, target, role):
        raise PermissionDenied
    try:
        await session.execute(
            text("SELECT arizonix.change_workspace_member_role(:workspace_id, :user_id, :role)"),
            {"workspace_id": workspace_id, "user_id": user_id, "role": role.value},
        )
    except DBAPIError as error:
        translate_database_error(error)


async def remove_member(session: AsyncSession, workspace_id: UUID, user_id: UUID) -> None:
    current = await actor_role(session, workspace_id)
    target = await target_role(session, workspace_id, user_id)
    if not can_remove_member(current, target):
        raise PermissionDenied
    try:
        await session.execute(
            text("SELECT arizonix.remove_workspace_member(:workspace_id, :user_id)"),
            {"workspace_id": workspace_id, "user_id": user_id},
        )
    except DBAPIError as error:
        translate_database_error(error)


async def leave_workspace(session: AsyncSession, workspace_id: UUID) -> None:
    await actor_role(session, workspace_id)
    try:
        await session.execute(
            text("SELECT arizonix.leave_workspace(:workspace_id)"),
            {"workspace_id": workspace_id},
        )
    except DBAPIError as error:
        translate_database_error(error)
