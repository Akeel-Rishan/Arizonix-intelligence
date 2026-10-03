import base64
import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from arizonix_api.authorization.permissions import can_mutate_company
from arizonix_api.db.models.companies import Company
from arizonix_api.schemas.companies import (
    ArchiveFilter,
    CompanyCreate,
    CompanyListItem,
    CompanyPage,
    CompanyResponse,
    CompanyUpdate,
)
from arizonix_api.services.errors import (
    CompanyNotFound,
    InvalidCompanyQuery,
    PermissionDenied,
    translate_database_error,
)
from arizonix_api.services.memberships import actor_role


def _filter_key(
    *, archive: ArchiveFilter, search: str | None, industry: str | None, country_code: str | None
) -> str:
    canonical = json.dumps(
        [archive.value, search or "", industry or "", country_code or ""], separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _encode_cursor(company: Company, filter_key: str) -> str:
    value = [company.created_at.astimezone(UTC).isoformat(), str(company.id), filter_key]
    encoded = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
    return encoded.decode().rstrip("=")


def _decode_cursor(cursor: str, filter_key: str) -> tuple[datetime, UUID]:
    if not cursor or len(cursor) > 512:
        raise InvalidCompanyQuery
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        value = json.loads(raw)
        if not isinstance(value, list) or len(value) != 3 or value[2] != filter_key:
            raise ValueError
        created_at = datetime.fromisoformat(value[0])
        if created_at.tzinfo is None:
            raise ValueError
        return created_at, UUID(value[1])
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise InvalidCompanyQuery from error


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _authorize_write(session: AsyncSession, workspace_id: UUID) -> None:
    if not can_mutate_company(await actor_role(session, workspace_id)):
        raise PermissionDenied


async def list_companies(
    session: AsyncSession,
    workspace_id: UUID,
    *,
    limit: int,
    cursor: str | None,
    archive: ArchiveFilter,
    search: str | None,
    industry: str | None,
    country_code: str | None,
) -> CompanyPage:
    await actor_role(session, workspace_id)
    normalized_search = search.strip() if search else None
    normalized_industry = industry.strip() if industry else None
    normalized_country = country_code.strip().upper() if country_code else None
    filter_key = _filter_key(
        archive=archive,
        search=normalized_search,
        industry=normalized_industry,
        country_code=normalized_country,
    )
    statement = select(Company).where(Company.workspace_id == workspace_id)
    if archive == ArchiveFilter.ACTIVE:
        statement = statement.where(Company.archived_at.is_(None))
    elif archive == ArchiveFilter.ARCHIVED:
        statement = statement.where(Company.archived_at.is_not(None))
    if normalized_search:
        statement = statement.where(
            Company.name.ilike(f"%{_escape_like(normalized_search)}%", escape="\\")
        )
    if normalized_industry:
        statement = statement.where(
            Company.industry.ilike(_escape_like(normalized_industry), escape="\\")
        )
    if normalized_country:
        statement = statement.where(Company.country_code == normalized_country)
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor, filter_key)
        statement = statement.where(
            or_(
                Company.created_at < cursor_time,
                and_(Company.created_at == cursor_time, Company.id < cursor_id),
            )
        )
    result = await session.scalars(
        statement.order_by(Company.created_at.desc(), Company.id.desc()).limit(limit + 1)
    )
    rows = list(result)
    page_rows = rows[:limit]
    return CompanyPage(
        items=[CompanyListItem.model_validate(company) for company in page_rows],
        next_cursor=_encode_cursor(page_rows[-1], filter_key) if len(rows) > limit else None,
    )


async def get_company(
    session: AsyncSession, workspace_id: UUID, company_id: UUID
) -> CompanyResponse:
    await actor_role(session, workspace_id)
    company = await session.scalar(
        select(Company).where(Company.workspace_id == workspace_id, Company.id == company_id)
    )
    if company is None:
        raise CompanyNotFound
    return CompanyResponse.model_validate(company)


async def create_company(
    session: AsyncSession, workspace_id: UUID, payload: CompanyCreate
) -> CompanyResponse:
    await _authorize_write(session, workspace_id)
    try:
        company_id = await session.scalar(
            text(
                "SELECT arizonix.create_company(:workspace_id, :name, :website_url, :industry, "
                ":country_code, :description, :notes)"
            ),
            {"workspace_id": workspace_id, **payload.model_dump()},
        )
    except DBAPIError as error:
        translate_database_error(error)
    return await get_company(session, workspace_id, company_id)


async def update_company(
    session: AsyncSession, workspace_id: UUID, company_id: UUID, payload: CompanyUpdate
) -> CompanyResponse:
    await _authorize_write(session, workspace_id)
    provided = payload.model_fields_set
    values = payload.model_dump()
    parameters: dict[str, object] = {
        "workspace_id": workspace_id,
        "company_id": company_id,
        "expected_version": payload.expected_version,
    }
    arguments: list[str] = [":workspace_id", ":company_id", ":expected_version"]
    for field in ("name", "website_url", "industry", "country_code", "description", "notes"):
        parameters[f"set_{field}"] = field in provided
        parameters[field] = values[field]
        arguments.extend([f":set_{field}", f":{field}"])
    try:
        await session.execute(
            text(f"SELECT arizonix.update_company({', '.join(arguments)})"), parameters
        )
    except DBAPIError as error:
        translate_database_error(error)
    return await get_company(session, workspace_id, company_id)


async def set_company_archived(
    session: AsyncSession,
    workspace_id: UUID,
    company_id: UUID,
    *,
    expected_version: int,
    archived: bool,
) -> CompanyResponse:
    await _authorize_write(session, workspace_id)
    try:
        await session.execute(
            text(
                "SELECT arizonix.set_company_archived("
                ":workspace_id, :company_id, :expected_version, :archived)"
            ),
            {
                "workspace_id": workspace_id,
                "company_id": company_id,
                "expected_version": expected_version,
                "archived": archived,
            },
        )
    except DBAPIError as error:
        translate_database_error(error)
    return await get_company(session, workspace_id, company_id)
