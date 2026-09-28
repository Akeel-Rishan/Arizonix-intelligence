"""Idempotently provision the non-login owner and restricted runtime database roles."""

import asyncio
import os

import asyncpg

OWNER_ROLE = "arizonix_owner"
RUNTIME_ROLE = "arizonix_runtime"


async def main() -> None:
    url = os.environ.get("ARIZONIX_MIGRATION_DATABASE_URL", "")
    password = os.environ.get("ARIZONIX_RUNTIME_DATABASE_PASSWORD", "")
    if not url or not password:
        raise SystemExit(
            "ARIZONIX_MIGRATION_DATABASE_URL and ARIZONIX_RUNTIME_DATABASE_PASSWORD are required"
        )
    dsn = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(dsn)
    try:
        await connection.execute(
            f"""
            DO $bootstrap$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{OWNER_ROLE}') THEN
                CREATE ROLE {OWNER_ROLE} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                  NOINHERIT NOREPLICATION NOBYPASSRLS;
              END IF;
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                CREATE ROLE {RUNTIME_ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                  NOINHERIT NOREPLICATION NOBYPASSRLS;
              END IF;
            END
            $bootstrap$;
            """
        )
        password_literal = await connection.fetchval("SELECT quote_literal($1)", password)
        await connection.execute(f"ALTER ROLE {RUNTIME_ROLE} PASSWORD {password_literal}")
        await connection.execute(f"REVOKE {OWNER_ROLE} FROM {RUNTIME_ROLE}")
    finally:
        await connection.close()
    print("Database roles are ready; no password was written to source or output.")


if __name__ == "__main__":
    asyncio.run(main())
