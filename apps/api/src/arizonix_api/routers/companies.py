from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from arizonix_api.authorization.dependencies import AuthenticatedSession
from arizonix_api.schemas.companies import (
    ArchiveFilter,
    CompanyCreate,
    CompanyLifecycleRequest,
    CompanyPage,
    CompanyResponse,
    CompanyUpdate,
)
from arizonix_api.services import companies

router = APIRouter(prefix="/workspaces/{workspace_id}/companies", tags=["companies"])
PageLimit = Annotated[int, Query(ge=1, le=100)]
OptionalFilter = Annotated[str | None, Query(max_length=100)]


@router.get("", response_model=CompanyPage)
async def list_companies(
    workspace_id: UUID,
    session: AuthenticatedSession,
    response: Response,
    limit: PageLimit = 25,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    archive: ArchiveFilter = ArchiveFilter.ACTIVE,
    search: OptionalFilter = None,
    industry: OptionalFilter = None,
    country_code: Annotated[
        str | None, Query(min_length=2, max_length=2, pattern="^[A-Za-z]{2}$")
    ] = None,
) -> CompanyPage:
    response.headers["Cache-Control"] = "private, no-store"
    return await companies.list_companies(
        session,
        workspace_id,
        limit=limit,
        cursor=cursor,
        archive=archive,
        search=search,
        industry=industry,
        country_code=country_code,
    )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    workspace_id: UUID,
    payload: CompanyCreate,
    session: AuthenticatedSession,
    response: Response,
) -> CompanyResponse:
    response.headers["Cache-Control"] = "no-store"
    return await companies.create_company(session, workspace_id, payload)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    workspace_id: UUID, company_id: UUID, session: AuthenticatedSession, response: Response
) -> CompanyResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await companies.get_company(session, workspace_id, company_id)


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    workspace_id: UUID,
    company_id: UUID,
    payload: CompanyUpdate,
    session: AuthenticatedSession,
    response: Response,
) -> CompanyResponse:
    response.headers["Cache-Control"] = "no-store"
    return await companies.update_company(session, workspace_id, company_id, payload)


@router.post("/{company_id}/archive", response_model=CompanyResponse)
async def archive_company(
    workspace_id: UUID,
    company_id: UUID,
    payload: CompanyLifecycleRequest,
    session: AuthenticatedSession,
    response: Response,
) -> CompanyResponse:
    response.headers["Cache-Control"] = "no-store"
    return await companies.set_company_archived(
        session,
        workspace_id,
        company_id,
        expected_version=payload.expected_version,
        archived=True,
    )


@router.post("/{company_id}/restore", response_model=CompanyResponse)
async def restore_company(
    workspace_id: UUID,
    company_id: UUID,
    payload: CompanyLifecycleRequest,
    session: AuthenticatedSession,
    response: Response,
) -> CompanyResponse:
    response.headers["Cache-Control"] = "no-store"
    return await companies.set_company_archived(
        session,
        workspace_id,
        company_id,
        expected_version=payload.expected_version,
        archived=False,
    )
