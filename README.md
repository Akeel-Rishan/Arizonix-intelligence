# Arizonix Intelligence

Arizonix Intelligence is an evidence-driven client research platform. The current implementation provides a reproducible local foundation with Supabase email/password authentication, protected application routes, a locally verified API identity boundary, typed domain contracts, synthetic evaluation fixtures, automated quality checks, optional containers, and CI definitions.

It does not yet include application database tables, workspace membership or roles, agents, scraping, outreach, external research providers, deployment, or complete production security controls.

## Direct local development

Direct development does not require Docker. From the repository root:

```powershell
uv sync --project apps/api --frozen
npm ci --prefix apps/web
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env.local
```

Start the API and web application in separate terminals:

```powershell
Set-Location apps/api
uv run uvicorn arizonix_api.main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
Set-Location apps/web
npm run dev
```

- Dashboard: <http://127.0.0.1:3000>
- API health: <http://127.0.0.1:8000/api/v1/health>
- FastAPI documentation: <http://127.0.0.1:8000/docs>

Before signing in, replace the Supabase placeholders in both copied environment files and complete the dashboard settings in [authentication.md](docs/authentication.md). The full environment contract is in [configuration.md](docs/configuration.md). Missing auth configuration fails closed with setup guidance; health remains public.

See [development.md](docs/development.md) for macOS/Linux commands, browser tests, supported runtimes, and troubleshooting.

## Optional Docker Compose

Docker runs only the API and web application. It is a production-build smoke environment, not a hot-reload workflow.

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
```

Stop it with:

```powershell
docker compose down
```

Browser-visible `NEXT_PUBLIC_API_BASE_URL` is embedded while the web image builds. After changing it or either host port, rebuild the web image. Compose service names such as `api` are not valid browser-facing URLs.

## Quality checks

Backend, from `apps/api`:

```powershell
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python -m arizonix_api.evaluation
```

Frontend, from `apps/web`:

```powershell
npm ci
npm run lint
npm run format:check
npm run test:config
npm run test:auth
npm run typecheck
npm run build
npm run test:e2e
```

The opt-in real-process browser check is documented in [development.md](docs/development.md). Configuration ownership and precedence are documented in [configuration.md](docs/configuration.md).

Core semantics and decisions are documented in [domain-model.md](docs/domain-model.md) and the
[ADR index](docs/adr/README.md). The provisional roadmap mapping is in
[requirements-coverage.md](docs/requirements-coverage.md). Evaluation fixtures and the important limit
of structural validation are described in [evals/README.md](evals/README.md).

Authentication is implemented as a narrow identity boundary, not a complete authorization system. Do not treat this foundation or its Compose workflow as production-ready.
