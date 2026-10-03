# Development progress

## Step status

- Step 1.1: **user-verified**
- Step 1.2: **user-verified**
- Step 1.3: **user-verified**
- Step 2.1: **user-verified**
- Step 2.2: **user-verified**
- Step 2.3: **user-verified**
- Step 3.1: **awaiting user verification**

## Completed foundation

Step 1.1 established the FastAPI liveness API, responsive Next.js dashboard shell, real health
connection, tests, and initial documentation. Step 1.2 established centralized configuration, direct
development commands, optional two-service Compose, quality checks, browser integration, CI, and
development documentation. The user confirmed both steps complete.

## Step 1.3 scope implemented

- Six accepted ADRs record modular boundaries, planned persistence/workspace isolation, evidence
  semantics, planned workflow recovery, planned provider-independent model boundaries, and versioned
  human approval. Every ADR distinguishes implemented contracts from future operational controls.
- Framework-independent Pydantic 2 domain contract version 1.0 covers companies, projects, runs,
  sources, snapshots, evidence, versioned claims and evidence links, and human-review decisions.
- Explicit assembled-record validation checks references, workspace/company ownership, claim versions,
  contradictory duplicate links, and supporting references for structurally verified claims.
- A generated JSON Schema and 12 small synthetic cases cover historical and weak evidence, positive
  evidence, identity separation, syndication, availability, current failures, contradictory fixes,
  unknown dates, unsupported financial estimates, prompt injection, and no-opportunity outcomes.
- The offline validation command checks schema drift, versions, fixture fields, case IDs, contracts,
  references, and ownership without network or model calls.
- A provisional requirements register follows the available build sequence and does not invent roadmap
  step numbers.
- README, architecture, development, domain, evaluation, and CI documentation now expose the contracts
  and verification commands.

No database model, migration, Supabase integration, authentication, business API route, research job,
worker, source collector, agent, model provider, dashboard feature, message, or outbound operation was
added.

## Step 1.3 verification record

Executed locally on 2026-09-28.

| Check                        | Command                                    | Outcome                                                                    |
| ---------------------------- | ------------------------------------------ | -------------------------------------------------------------------------- |
| Backend lint                 | `uv run ruff check .`                      | PASS                                                                       |
| Backend formatting           | `uv run ruff format --check .`             | PASS; 21 Python files checked                                              |
| Backend tests                | `uv run pytest`                            | PASS; 32 tests passed                                                      |
| Fixture/schema validation    | `uv run python -m arizonix_api.evaluation` | PASS; 12 synthetic cases validated offline                                 |
| Frontend lint                | `npm run lint`                             | PASS                                                                       |
| Frontend formatting          | `npm run format:check`                     | PASS                                                                       |
| Frontend configuration tests | `npm run test:config`                      | PASS; 3 tests passed                                                       |
| Frontend type-check          | `npm run typecheck`                        | PASS                                                                       |
| Frontend production build    | `npm run build`                            | PASS; all six application routes generated                                 |
| Full proposal coverage       | Repository Markdown/text search            | NOT RUN; source search completed, but the authoritative proposal is absent |
| Browser/visual regression    | Playwright and manual viewport review      | NOT RUN; no frontend/shared UI code changed in Step 1.3                    |
| Docker build/start           | Compose smoke environment                  | NOT RUN; infrastructure did not change in Step 1.3                         |
| Hosted GitHub Actions        | Push or pull request run                   | NOT RUN; workflow was updated locally and not pushed                       |
| Model behavior evaluation    | Actual system outputs against expectations | NOT IMPLEMENTED; no model or agent exists                                  |

The backend suite still emits one upstream FastAPI/Starlette warning about the future `httpx2`
transition. The built-in Node TypeScript test still emits its experimental/module-detection warning.
Neither changes the passing outcomes.

## Proposal coverage limitation

The full project proposal and numbered roadmap are not present in the repository. The coverage map in
`docs/requirements-coverage.md` is provisional and derived only from the Step 1.3 brief. Add the
authoritative original at `docs/project-proposal.md`; then reconcile real section numbers and titles
without replacing or paraphrasing the source.

## Step 2.1 scope implemented

Step 2.1 adds Supabase email/password SSR authentication, email confirmation, safe redirects, local sign-out, protected application routes, a verified FastAPI bearer boundary, `/api/v1/me`, bounded JWKS caching, offline auth tests, and dashboard setup documentation. It deliberately does not add database tables, workspaces, roles, RLS, business records, agents, or outreach.

Live Supabase verification is not run automatically because the repository contains no committed real project credentials. The deterministic browser suite uses the actual Supabase client libraries against a local protocol-compatible mock and does not add an auth bypass.

## Step 2.1 verification record

Executed locally on 2026-09-28.

| Check                                                                    | Outcome                                                               |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| Backend Ruff lint and format                                             | PASS; 27 Python files checked                                         |
| Backend tests                                                            | PASS; 46 tests with generated signing keys and mocked JWKS            |
| Synthetic fixture validation                                             | PASS; 12 offline cases                                                |
| Frontend ESLint and Prettier                                             | PASS                                                                  |
| Frontend configuration tests                                             | PASS; 5 tests                                                         |
| Frontend redirect-security tests                                         | PASS; 2 tests                                                         |
| Frontend TypeScript                                                      | PASS                                                                  |
| Next.js production build                                                 | PASS; protected routes are dynamically rendered                       |
| Deterministic browser suite plus real API lifecycle                      | PASS; 13 tests, with the separately gated invalid-config case skipped |
| Separately gated invalid-config browser case                             | PASS; 1 test                                                          |
| Compose configuration rendering                                          | PASS; Docker reported only a local config-file permission warning     |
| Real Supabase registration, email delivery, session refresh, and sign-in | **NOT RUN**; no real project credentials were supplied                |
| Docker image build/start                                                 | NOT RUN                                                               |
| Hosted GitHub Actions                                                    | NOT RUN; changes have not been pushed                                 |

The test-only Supabase-compatible server validates application flows using the real Supabase SDK and SSR cookies, but it does not prove live provider configuration or email delivery. The real-process API lifecycle check uses an isolated port so an existing development API cannot invalidate its CORS result.

## Step 2.2 scope implemented

- Async SQLAlchemy runtime access and Alembic migrations with separate privileged migration and
  restricted runtime credentials.
- Minimal users, workspaces, memberships, an explicit role matrix, atomic first-owner creation,
  serialized last-owner protection, RLS, exact grants, and guarded functions.
- Workspace APIs, onboarding, switching, responsive settings, existing-user UUID membership flow,
  role controls, confirmations, and cache clearing on sign-out.
- An opt-in PostgreSQL Compose profile and CI PostgreSQL service with fresh migrations and restricted
  role integration tests.

## Step 2.2 verification record

Executed locally on 2026-09-28.

| Check                                        | Outcome                                                                        |
| -------------------------------------------- | ------------------------------------------------------------------------------ |
| Backend Ruff lint/format                     | PASS                                                                           |
| Backend unit and PostgreSQL tests            | PASS; 63 passed with the restricted runtime role                               |
| Frontend ESLint/Prettier/TypeScript          | PASS                                                                           |
| Next.js production build                     | PASS; onboarding and all protected routes generated                            |
| Mocked workspace browser tests               | PASS; 4 tests                                                                  |
| Default deterministic browser suite          | PASS; 16 tests passed, 2 separately gated                                      |
| Invalid-config and real-API lifecycle gates  | PASS; 1 test in each isolated run                                              |
| Fresh Alembic migration                      | PASS; applied to disposable PostgreSQL 17 from empty state                     |
| Real PostgreSQL/RLS integration tests        | PASS; 3 tests cover RLS, privileges, concurrency, pooling, and HTTP boundaries |
| Hosted Supabase migration and two-user check | **NOT RUN**; remote credentials were not used automatically                    |
| Hosted GitHub Actions                        | **NOT RUN**; changes have not been pushed                                      |

Mocked browser results do not prove RLS; the separate PostgreSQL results above do. CI is configured to
repeat the fresh migration and restricted-role suite. Hosted Supabase remains a separate user-run check.

## Step 2.3 scope implemented

- Atomic, append-only audit events for every workspace/membership mutation, including explicit no-op,
  creation, removal, and voluntary-leave semantics.
- Runtime-role write denial, owner/admin RLS reads, request correlation, bounded safe payloads, and
  redacted structured security logs.
- Cursor-paginated owner/admin audit API and responsive Settings history with server-side filters.
- Restricted-role PostgreSQL integrity/authorization regression tests and mocked browser coverage.

Step 2.3 was confirmed by the user before Step 3.1 began.

## Step 2.3 verification record

Executed locally on 2026-10-03 against an isolated PostgreSQL 17 Compose project. The user's existing
local database volume was not modified.

| Check                                     | Outcome                                                        |
| ----------------------------------------- | -------------------------------------------------------------- |
| Backend Ruff lint and format              | PASS; 62 Python files formatted                                |
| Backend full test suite                   | PASS; 66 tests                                                 |
| Real PostgreSQL/RLS/audit tests           | PASS; 5 tests with the restricted runtime role                 |
| Step 2.2 revision to audit-head migration | PASS; `20260928_0001` → `20261003_0002`                        |
| Fresh complete Alembic chain              | PASS; empty disposable database reached `20261003_0002`        |
| Frontend ESLint, Prettier, and TypeScript | PASS                                                           |
| Frontend configuration/auth helper tests  | PASS; 7 tests                                                  |
| Next.js production build                  | PASS; `/settings/audit` is a protected dynamic route           |
| Default mocked browser suite              | PASS; 18 tests, 2 separately gated                             |
| Focused workspace/audit browser suite     | PASS; 6 tests including target responsive widths               |
| Real API process lifecycle browser gate   | PASS; 1 test                                                   |
| Interactive in-app browser inspection     | **NOT RUN**; no browser session was connected                  |
| Live Supabase/provider verification       | **NOT RUN**; no remote credentials or production database used |
| Hosted GitHub Actions                     | **NOT RUN**; changes have not been pushed                      |

Mocked browser checks prove the UI behavior but not PostgreSQL isolation. The separate restricted-role
PostgreSQL checks above verify RLS, privilege denial, audit atomicity, and rollback behavior.

## Step 3.1 scope implemented

- Workspace-scoped company creation, stable cursor listing, bounded literal search, industry/country
  filters, full detail, partial editing, reversible archive/restore, and optimistic versions.
- Owner/admin/analyst mutations and viewer reads enforced in the UI, application services, RLS,
  grants, and guarded database functions.
- Atomic company audit actions with safe detail allowlists; list responses exclude private notes.
- Responsive Prospects list/create/detail/edit flows with URL-backed filters, stale-request cancellation,
  actionable empty/error states, and archive confirmation.
- Focused schema, real PostgreSQL, and mocked browser regression coverage.

Step 3.1 is awaiting user verification.

## Step 3.1 verification record

Executed locally on 2026-10-03 against an isolated PostgreSQL 17 Compose project. The configured
development database and hosted Supabase project were not migrated.

| Check                                           | Outcome                                                 |
| ----------------------------------------------- | ------------------------------------------------------- |
| Fresh Alembic chain                             | PASS; empty disposable database reached `20261003_0003` |
| Backend Ruff lint                               | PASS                                                    |
| Backend full suite with real PostgreSQL         | PASS; 79 tests                                          |
| Company RLS/permissions/concurrency/audit test  | PASS with restricted runtime role                       |
| Frontend ESLint and TypeScript                  | PASS                                                    |
| Next.js production build                        | PASS; all four Prospects routes generated               |
| Default mocked browser suite                    | PASS; 22 tests, 2 separately gated                      |
| Company responsive browser coverage             | PASS at 375, 768, and 1440 px                           |
| Interactive in-app browser inspection           | NOT RUN; automated Chromium coverage was used           |
| Hosted migration and live Supabase verification | NOT RUN; remote systems were not changed                |
| Hosted GitHub Actions                           | NOT RUN; changes have not been pushed                   |

## Next planned step

Step 3.2: company locations, canonical domains, duplicate prevention, and entity resolution. These are
not implemented in Step 3.1.
