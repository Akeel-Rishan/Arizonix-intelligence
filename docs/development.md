# Development guide

## Supported runtimes

| Tool           | Supported                          | Verified locally           |
| -------------- | ---------------------------------- | -------------------------- |
| Python         | 3.12-3.14                          | uv-managed CPython 3.12.13 |
| uv             | 0.11.x or newer compatible release | 0.11.14                    |
| Node.js        | 22-24                              | 22.22.0                    |
| npm            | 10 or newer                        | 10.9.4                     |
| Docker Engine  | Compose-compatible current release | 29.4.0                     |
| Docker Compose | v2                                 | 5.1.2                      |

The Python and Node container images are pinned to Python 3.12.13 and Node.js 22.22.0. Lockfiles determine application dependencies.

## Direct setup

Direct local development is the primary workflow and does not require Docker.

Windows PowerShell, from the repository root:

```powershell
uv sync --project apps/api --frozen
npm ci --prefix apps/web
npx --prefix apps/web playwright install chromium
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env.local
```

macOS/Linux:

```bash
uv sync --project apps/api --frozen
npm ci --prefix apps/web
npx --prefix apps/web playwright install chromium
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Start the API:

```powershell
Set-Location apps/api
uv run uvicorn arizonix_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Use `cd apps/api` instead of `Set-Location apps/api` on macOS/Linux. Start the frontend from a second terminal:

```powershell
Set-Location apps/web
npm run dev
```

The default URLs are `http://127.0.0.1:3000` for the dashboard and `http://127.0.0.1:8000/api/v1/health` for API liveness. Replace the Supabase placeholders and complete the dashboard configuration described in [configuration.md](configuration.md) before using sign-up or sign-in.

## Command matrix

| Area     | Purpose             | Command                                    | Working directory |
| -------- | ------------------- | ------------------------------------------ | ----------------- |
| Backend  | Frozen install      | `uv sync --frozen`                         | `apps/api`        |
| Backend  | Lint                | `uv run ruff check .`                      | `apps/api`        |
| Backend  | Formatting check    | `uv run ruff format --check .`             | `apps/api`        |
| Backend  | Apply formatting    | `uv run ruff format .`                     | `apps/api`        |
| Backend  | Tests               | `uv run pytest`                            | `apps/api`        |
| Backend  | Fixture validation  | `uv run python -m arizonix_api.evaluation` | `apps/api`        |
| Frontend | Frozen install      | `npm ci`                                   | `apps/web`        |
| Frontend | Lint                | `npm run lint`                             | `apps/web`        |
| Frontend | Formatting check    | `npm run format:check`                     | `apps/web`        |
| Frontend | Apply formatting    | `npm run format`                           | `apps/web`        |
| Frontend | Configuration tests | `npm run test:config`                      | `apps/web`        |
| Frontend | Auth helper tests   | `npm run test:auth`                        | `apps/web`        |
| Frontend | Type-check          | `npm run typecheck`                        | `apps/web`        |
| Frontend | Production build    | `npm run build`                            | `apps/web`        |
| Browser  | Mocked smoke suite  | `npm run test:e2e`                         | `apps/web`        |

Quality-check commands do not modify source files. Only the explicit `format` commands write changes.

Evaluation validation is deterministic and offline. It checks committed schema drift, fixture shape,
contract versions, references, and ownership. It does not run a model or measure model behavior. Use
`uv run python -m arizonix_api.evaluation --write-schema` only after an intentional evaluation-contract
change, then inspect the generated schema diff.

## Browser integration

The normal Playwright suite starts Next.js on port 3100 and a deterministic test-only Supabase-compatible auth server on port 54321. It exercises real `@supabase/ssr` cookie behavior, successful and failed login, sign-up pending state, confirmation, sign-out, protection, safe redirects, navigation, API boundary states, and responsive layouts. It does not use a production auth bypass or external network access.

To run the real API restart and recovery test in PowerShell:

```powershell
Set-Location apps/web
$env:RUN_LIVE_INTEGRATION='1'
npm run test:e2e
Remove-Item Env:RUN_LIVE_INTEGRATION
```

On macOS/Linux:

```bash
cd apps/web
RUN_LIVE_INTEGRATION=1 npm run test:e2e
```

The live test starts the already-installed backend from `apps/api/.venv`, waits up to 15 seconds for readiness, verifies the real healthy response, stops the API to verify the honest error state, restarts it, and verifies retry recovery. It always attempts to stop the child API process.

## Docker Compose smoke environment

Copy the root Compose settings once:

```powershell
Copy-Item .env.example .env
```

Use `cp .env.example .env` on macOS/Linux. Then use Compose v2:

```powershell
docker compose config
docker compose up --build --wait
docker compose ps
docker compose logs --tail 100 api web
docker compose down
```

To rebuild after source, dependency, or public configuration changes:

```powershell
docker compose up --build --force-recreate --wait
```

Container hot reload is intentionally not configured. Source edits require rebuilding the affected image. The services run as non-root users, listen on `0.0.0.0` inside their containers, and publish to host loopback only.

## Troubleshooting

- Port conflict: change `API_HOST_PORT` or `WEB_HOST_PORT` in the relevant environment source. Also update the browser API origin and API CORS allowlist as described in [configuration.md](configuration.md).
- Dashboard reports the API is unavailable: open the health URL directly, verify the API process is running, and confirm `NEXT_PUBLIC_API_BASE_URL` is a host-reachable origin.
- CORS error: the browser page origin must exactly match an entry in `ARIZONIX_ALLOWED_ORIGINS`, including scheme, hostname, and port.
- Configuration error in the health card: set `NEXT_PUBLIC_API_BASE_URL` to an `http://` or `https://` origin without `/api/v1`, credentials, query parameters, or fragments, then restart development or rebuild the web image.
- Authentication setup screen: set `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and the matching server-side `ARIZONIX_SUPABASE_URL`, then restart both applications.
- Confirmation returns to sign-in: verify the dashboard Site URL, redirect allowlist, confirmation template, and exact host (`127.0.0.1` versus `localhost`) match the configured `NEXT_PUBLIC_SITE_URL`.
- Docker build cannot download packages or images: verify Docker Desktop or the Docker daemon has network access, then retry `docker compose build --no-cache`.
- Browser binary missing: run `npx playwright install chromium` locally or `npx playwright install --with-deps chromium` on Linux CI.
- Occupied Playwright port 3100: stop the unrelated process. CI disables server reuse so it cannot accidentally test another application.
