from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from arizonix_api.authorization.dependencies import AuthenticatedSession
from arizonix_api.schemas.memberships import (
    LeaveResponse,
    MemberAdd,
    MemberPage,
    MemberRoleUpdate,
)
from arizonix_api.services import memberships

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["workspace members"])

PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0, le=100_000)]


@router.get("/members", response_model=MemberPage)
async def list_members(
    workspace_id: UUID,
    session: AuthenticatedSession,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
) -> MemberPage:
    items, has_more = await memberships.list_members(
        session, workspace_id, limit=limit, offset=offset
    )
    return MemberPage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post("/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(
    workspace_id: UUID, payload: MemberAdd, session: AuthenticatedSession
) -> Response:
    await memberships.add_member(session, workspace_id, payload.user_id, payload.role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def change_member_role(
    workspace_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    session: AuthenticatedSession,
) -> Response:
    await memberships.change_member_role(session, workspace_id, user_id, payload.role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: UUID, user_id: UUID, session: AuthenticatedSession
) -> Response:
    await memberships.remove_member(session, workspace_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/leave", response_model=LeaveResponse)
async def leave_workspace(workspace_id: UUID, session: AuthenticatedSession) -> LeaveResponse:
    await memberships.leave_workspace(session, workspace_id)
    return LeaveResponse()
