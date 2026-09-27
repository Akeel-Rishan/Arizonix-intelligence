# Development progress

## Step status

- Step 1.1: **user-verified**
- Step 1.2: **awaiting user verification**

## Step 1.2 scope implemented

- Centralized, validated backend configuration for environment, version, log level, and explicit CORS origins.
- Centralized frontend public API origin parsing with normalization and useful invalid-configuration behavior.
- Tests isolated from developer `.env` files, with focused default, override, invalid, CORS, and public URL coverage.
- Prettier formatting and configuration-test scripts added alongside existing lint, type-check, build, and browser scripts.
- Optional two-service Docker Compose smoke environment with pinned runtime images, non-root processes, loopback publishing, health checks, and build-time browser configuration.
- Three-job GitHub Actions workflow for backend quality, frontend quality, and mocked plus real browser integration.
- Direct development, Compose, configuration, troubleshooting, and architecture documentation.
- Generated TypeScript build metadata moved under ignored `.next` output.

No database, Supabase, Redis, worker, LangGraph dependency, agent, source adapter, external provider, authentication, outreach, deployment, or business feature was added.

## Verification record

Executed locally on 2026-09-28 with Node.js 22.22.0, npm 10.9.4, uv 0.11.14, uv-managed Python 3.12.13, Docker CLI 29.4.0, Docker Compose 5.1.2, and Chromium 153 installed by Playwright.

| Check                              | Command                                                                                                  | Outcome                                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Backend frozen install             | `uv sync --frozen`                                                                                       | PASS. Locked environment checked without dependency changes.                                  |
| Backend lint                       | `uv run ruff check .`                                                                                    | PASS.                                                                                         |
| Backend formatting                 | `uv run ruff format --check .`                                                                           | PASS. 8 files formatted.                                                                      |
| Backend tests                      | `uv run pytest`                                                                                          | PASS. 11 tests passed.                                                                        |
| Frontend frozen install            | `npm ci --cache .npm-cache`                                                                              | PASS. 370 packages audited, zero vulnerabilities reported.                                    |
| Frontend lint                      | `npm run lint`                                                                                           | PASS.                                                                                         |
| Frontend formatting                | `npm run format:check`                                                                                   | PASS.                                                                                         |
| Public configuration tests         | `npm run test:config`                                                                                    | PASS. 3 tests passed.                                                                         |
| TypeScript                         | `npm run typecheck`                                                                                      | PASS.                                                                                         |
| Production build                   | `npm run build`                                                                                          | PASS. All six application routes generated with standalone output.                            |
| Browser smoke and live integration | `RUN_LIVE_INTEGRATION=1 npm run test:e2e`                                                                | PASS. 6 passed; the separately gated invalid-configuration test was skipped in this run.      |
| Invalid configuration UI           | `EXPECT_INVALID_PUBLIC_CONFIG=1 npx playwright test tests/e2e/configuration.spec.ts` with an invalid URL | PASS. 1 test passed.                                                                          |
| Direct startup                     | API on 8000 and web on 3000, then HTTP probes                                                            | PASS. API contract returned 200 and the overview page returned 200.                           |
| Responsive widths                  | Playwright at 375px, 768px, and 1440px                                                                   | PASS. Navigation remained usable and no page overflow was detected.                           |
| Compose validation                 | `docker compose config`                                                                                  | PASS. Two services, loopback ports, build argument, and health dependency resolved correctly. |
| Container build/start/health       | `docker compose up --build --wait`                                                                       | NOT RUN. Docker CLI was installed but the local daemon pipe was unavailable.                  |
| Browser-to-container API           | Browser against the healthy Compose stack                                                                | NOT RUN. Depends on the unavailable Docker daemon.                                            |
| Hosted GitHub Actions              | Push or pull request run                                                                                 | NOT RUN. The workflow was created locally and was not pushed.                                 |

The backend tests emit one upstream FastAPI/Starlette warning about the future `httpx2` transition. The built-in Node TypeScript test runner emits an experimental/module-detection warning. Neither warning changes the passing outcomes.

## Remaining manual verification

1. Start Docker Desktop or another compatible daemon.
2. Run `docker compose up --build --wait` from the repository root.
3. Run `docker compose ps` and confirm both services are healthy.
4. Open `http://127.0.0.1:3000` and confirm the health card connects to the containerized API.
5. Run `docker compose down`.
6. Push through the normal user workflow and verify all three hosted CI jobs.

## Next planned step

Step 1.3: architecture decisions, domain contracts, proposal coverage map, and evaluation fixtures.

Step 1.3 has not been implemented.
