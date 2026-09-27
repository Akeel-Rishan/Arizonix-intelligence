# Arizonix Intelligence

Arizonix Intelligence is an evidence-driven client research platform. This repository currently contains only the Step 1.1 local foundation: a FastAPI liveness API and a responsive Next.js application shell with a real browser-to-API health check.

No authentication, database, agents, scraping, outreach, deployment, or production security controls are implemented yet. Do not treat this foundation as production-ready.

## Runtime requirements

- Python 3.12, 3.13, or 3.14 (`>=3.12,<3.15`). Tested with Python 3.12.13 through uv.
- uv 0.11 or newer. Tested with uv 0.11.14.
- Node.js 22, 23, or 24 (`>=22,<25`). Tested with Node.js 22.22.0.
- npm 10 or newer. Tested with npm 10.9.4.
- Chromium is required only for the Playwright browser suite.

Dependency versions are pinned by [uv.lock](apps/api/uv.lock) and [package-lock.json](apps/web/package-lock.json). Notable direct versions include FastAPI 0.141.1, Next.js 16.3.6, React 19.2.4, Tailwind CSS 4.3.3, and Playwright 1.63.0.

## Install from the repository root

```powershell
uv sync --project apps/api --frozen
npm ci --prefix apps/web
npx --prefix apps/web playwright install chromium
```

Copy the harmless local examples in Windows PowerShell:

```powershell
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env.local
```

On macOS or Linux:

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

`NEXT_PUBLIC_API_BASE_URL` is sent to the browser. It must contain a public URL only, never a secret. The default frontend origin allowed by the API is exactly `http://127.0.0.1:3000`, with `http://localhost:3000` also accepted for local browser use. CORS never uses a wildcard.

## Run locally

Open two terminals at the repository root.

Backend:

```powershell
Set-Location apps/api
uv run uvicorn arizonix_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
Set-Location apps/web
npm run dev
```

The same commands work in macOS/Linux shells by replacing `Set-Location` with `cd`.

- Dashboard: <http://127.0.0.1:3000>
- API liveness: <http://127.0.0.1:8000/api/v1/health>
- FastAPI docs: <http://127.0.0.1:8000/docs>

The health endpoint reports process liveness only. It does not claim that a database, worker, or provider is ready.

## Quality commands

Run backend checks from `apps/api`:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Run frontend checks from `apps/web`:

```powershell
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

The browser suite starts the frontend on port 3100 so it does not collide with normal development on port 3000. Its regular smoke suite intercepts the API boundary to verify healthy, invalid, unavailable, and retry states. To also run the real-process recovery check after installing both applications:

```powershell
$env:RUN_LIVE_INTEGRATION='1'; npm run test:e2e
```

On macOS/Linux:

```bash
RUN_LIVE_INTEGRATION=1 npm run test:e2e
```

## Troubleshooting

- Occupied port: stop the process using port 3000 or 8000, or choose another port. If the frontend port changes, add that exact origin to `ARIZONIX_ALLOWED_ORIGINS` and restart the API.
- Incorrect API URL: confirm `apps/web/.env.local` uses the reachable API origin, normally `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`, then restart Next.js.
- CORS failure: the page origin must exactly match an entry in `ARIZONIX_ALLOWED_ORIGINS`. Scheme, hostname, and port all matter.
- Backend unavailable: start the FastAPI command, wait for startup to complete, then use **Retry connection** in the dashboard.
- Browser missing: run `npx playwright install chromium` from `apps/web`.

See [architecture.md](docs/architecture.md) for current boundaries and [development-progress.md](docs/development-progress.md) for the verification record.

