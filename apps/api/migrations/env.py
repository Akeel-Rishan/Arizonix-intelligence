import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from arizonix_api.db import models  # noqa: F401
from arizonix_api.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("ARIZONIX_MIGRATION_DATABASE_URL")
if not database_url:
    raise RuntimeError("ARIZONIX_MIGRATION_DATABASE_URL is required for migrations")
if not database_url.startswith("postgresql+asyncpg://"):
    raise RuntimeError("migration database URL must use postgresql+asyncpg")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are disabled; use a disposable database to validate SQL")
asyncio.run(run_async_migrations())
