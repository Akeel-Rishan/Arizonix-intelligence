# Database setup and migrations

## Credential separation

- `ARIZONIX_MIGRATION_DATABASE_URL` is a privileged PostgreSQL URL used only by bootstrap and Alembic.
- `ARIZONIX_DATABASE_URL` authenticates as `arizonix_runtime` and is the only URL used by FastAPI.
- `ARIZONIX_RUNTIME_DATABASE_PASSWORD` is read only by the idempotent role bootstrap command.

Never put these values in `NEXT_PUBLIC_*`, commit real passwords, use the Supabase service-role key as a
database credential, or give the migration URL to the running API.

## Disposable local PostgreSQL

From the repository root, start only the optional database profile:

```powershell
docker compose --profile database up -d db
Set-Location apps/api
$env:ARIZONIX_MIGRATION_DATABASE_URL='postgresql+asyncpg://postgres:local-dev-only@127.0.0.1:55432/arizonix'
$env:ARIZONIX_RUNTIME_DATABASE_PASSWORD='choose-a-local-runtime-password'
uv run python scripts/bootstrap_database.py
uv run alembic upgrade head
```

Set the matching restricted URL in `apps/api/.env`:

```dotenv
ARIZONIX_DATABASE_URL=postgresql+asyncpg://arizonix_runtime:choose-a-local-runtime-password@127.0.0.1:55432/arizonix
```

The bootstrap is idempotent and rotates the supplied runtime password. It creates a non-login object
owner and a restricted login runtime role; migrations contain no password. To run the real RLS suite:

```powershell
$env:ARIZONIX_TEST_MIGRATION_DATABASE_URL=$env:ARIZONIX_MIGRATION_DATABASE_URL
$env:ARIZONIX_TEST_RUNTIME_DATABASE_URL=$env:ARIZONIX_DATABASE_URL
uv run pytest -m postgres
```

Stop the database with `docker compose --profile database down`. Add `-v` only when intentionally
discarding the local database volume.

## Hosted Supabase procedure

Do not run these commands until the URLs and target project have been checked. From `apps/api`:

```powershell
$env:ARIZONIX_MIGRATION_DATABASE_URL='postgresql+asyncpg://PRIVILEGED_USER:URL_ENCODED_PASSWORD@HOST:5432/postgres'
$env:ARIZONIX_RUNTIME_DATABASE_PASSWORD='LONG_RANDOM_RUNTIME_PASSWORD'
uv run python scripts/bootstrap_database.py
uv run alembic upgrade head
```

Then configure FastAPI with a direct or session-pooler URL for `arizonix_runtime`; do not reuse the
privileged URL. Supabase recommends direct connections for persistent servers when IPv6 is available,
or the session pooler for persistent IPv4 clients. Do not use the shared transaction pooler on port
6543 with SQLAlchemy's asyncpg dialect: disabling both statement caches does not remove the dialect's
use of prepared statements, while transaction mode does not support them. Migrations also require a
direct/session connection. URL-encode passwords containing reserved URI characters.

Migration `20260928_0001` creates the schema, tables, constraints, indexes, triggers, RLS policies,
guarded functions, and exact grants. The `alembic_version` table records application order. Alembic is
the repository's only migration system.

## User and RLS behavior

`application_users` contains UUID, optional display email, and timestamps—never passwords or copied JWT
payloads. `workspaces` contains stable UUID, name, creator and timestamps. `memberships` has a composite
workspace/user primary key, constrained role enum, foreign keys and lookup index. All timestamps are
timezone-aware with server defaults.

RLS reads `arizonix.current_user_id()`, which parses only transaction-local
`current_setting('arizonix.user_id', true)`. Missing context evaluates to no rows. Security-definer
membership helpers avoid policy recursion; they return booleans and cannot mutate data. Direct runtime
writes are denied by grants even before an RLS write policy is considered.

CI starts a disposable PostgreSQL 17 service, provisions the exact restricted role, applies migrations
from an empty database, and runs the integration tests. Mocked browser tests are separate and do not
prove hosted Supabase behavior.
