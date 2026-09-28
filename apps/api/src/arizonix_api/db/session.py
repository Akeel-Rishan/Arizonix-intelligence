from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from arizonix_api.auth.dependencies import CurrentPrincipal
from arizonix_api.config import Settings


@dataclass(slots=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]

    async def dispose(self) -> None:
        await self.engine.dispose()


def build_database(settings: Settings) -> Database | None:
    if settings.database_url is None:
        return None
    connect_args = (
        {"prepared_statement_cache_size": 0, "statement_cache_size": 0}
        if settings.database_disable_statement_cache
        else {}
    )
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        connect_args=connect_args,
    )
    return Database(engine=engine, sessions=async_sessionmaker(engine, expire_on_commit=False))


async def authenticated_session(
    request: Request, principal: CurrentPrincipal
) -> AsyncIterator[AsyncSession]:
    database: Database | None = request.app.state.database
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    async with database.sessions() as session, session.begin():
        await session.execute(
            text("SELECT set_config('arizonix.user_id', :user_id, true)"),
            {"user_id": str(principal.user_id)},
        )
        await session.execute(
            text("SELECT arizonix.provision_application_user(:user_id, :email)"),
            {"user_id": principal.user_id, "email": principal.email},
        )
        yield session
