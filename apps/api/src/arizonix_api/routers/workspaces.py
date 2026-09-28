from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from arizonix_api.authorization.dependencies import AuthenticatedSession
from arizonix_api.schemas.workspaces import (
    WorkspaceCreate,
    WorkspacePage,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from arizonix_api.services import workspaces

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0, le=100_000)]


@router.get("", response_model=WorkspacePage)
async def list_workspaces(
    session: AuthenticatedSession, limit: PageLimit = 50, offset: PageOffset = 0
) -> WorkspacePage:
    items, has_more = await workspaces.list_workspaces(session, limit=limit, offset=offset)
    return WorkspacePage(items=items, limit=limit, offset=offset, has_more=has_more)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, session: AuthenticatedSession, response: Response
) -> WorkspaceResponse:
    response.headers["Cache-Control"] = "no-store"
    return await workspaces.create_workspace(session, payload.name)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: UUID, session: AuthenticatedSession) -> WorkspaceResponse:
    return await workspaces.get_workspace(session, workspace_id)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def rename_workspace(
    workspace_id: UUID, payload: WorkspaceUpdate, session: AuthenticatedSession
) -> WorkspaceResponse:
    return await workspaces.rename_workspace(session, workspace_id, payload.name)
