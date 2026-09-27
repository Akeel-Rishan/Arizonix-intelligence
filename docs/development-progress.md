# Development progress

## Current step

Step 1.1: local application foundation

Status: **awaiting user verification**

## Scope implemented

- FastAPI application factory, typed settings, explicit API metadata, restricted CORS, and `GET /api/v1/health` liveness contract.
- Isolated pytest coverage for the health contract, allowed and denied CORS origins, and comma-separated environment configuration.
- Next.js App Router shell with strict TypeScript, Tailwind CSS, semantic landmarks, skip link, active navigation, responsive drawer, focus management, and reduced-motion handling.
- Real typed frontend health client with cancellation, five-second timeout, contract validation, honest failures, duplicate-request prevention, and manual retry.
- Six working application destinations with honest empty states and no fabricated business data.
- Playwright smoke coverage for routing, valid and invalid API responses, network failure, retry, mobile navigation, keyboard behavior, and overflow at 375px, 768px, and 1440px.
- An opt-in live integration test that starts the real backend, verifies success, stops it to verify the failure state, restarts it, and verifies retry recovery.
- Reproducible Python and npm lockfiles plus local setup and architecture documentation.

No full project proposal was present in the repository at implementation time. The supplied Step 1.1 brief was used without inventing later-step requirements.

## Verification record

Executed on 2026-09-27 with Node.js 22.22.0, npm 10.9.4, uv 0.11.14, and uv-managed Python 3.12.13.

| Command | Outcome |
| --- | --- |
| `uv lock` | PASS. Resolved 31 packages and created `apps/api/uv.lock`. |
| `uv sync --frozen` | PASS. Installed the exact locked backend environment. |
| `uv run pytest` | PASS. 4 tests passed. One upstream FastAPI/Starlette deprecation warning notes the future `httpx2` transition. |
| `uv run ruff check .` | PASS. |
| `uv run ruff format --check .` | PASS. 8 files already formatted. |
| `npm ci` / lockfile install equivalence | PASS. `npm install` created the lockfile; the final clean-install check uses `npm ci`. |
| `npm run lint` | PASS. |
| `npm run typecheck` | PASS. |
| `npm run build` | PASS. Next.js generated `/`, `/prospects`, `/research`, `/evidence`, `/review`, and `/settings`. |
| `npm run test:e2e` | PASS. Intercepted browser smoke suite passed; live integration is skipped unless explicitly enabled. |
| `RUN_LIVE_INTEGRATION=1 npm run test:e2e` | PASS. Real backend success, outage, restart, and retry recovery were verified. |

The dependency selection was checked against current official release information. TypeScript is intentionally pinned to the compatible 6.x line and ESLint to 9.x because the current Next.js 16.3.6 lint stack does not yet support TypeScript 7 through its bundled parser.

## Remaining manual checks

- User review of appearance, copy, and keyboard flow in their preferred browser and operating system.
- User confirmation that ports 3000 and 8000 are available in their local setup.
- Dark mode is not part of this light-theme application-shell brief and was not added.

## Next planned step

Step 1.2: development infrastructure, configuration, CI, and quality checks.

Step 1.2 has not been implemented.

