# Architecture

## Implemented foundation

Arizonix Intelligence currently consists of two independently deployable applications:

```text
Browser at 127.0.0.1:3000
  |                 |
  | Supabase SSR   | GET /api/v1/health (public)
  | session        | GET /api/v1/me + Bearer access JWT
  v                 v
Supabase Auth      FastAPI at 127.0.0.1:8000
                         |
                         | asymmetric JWKS verification
                         v
                  Supabase Auth JWKS
                         |
                         | verified subject -> transaction-local identity
                         v
              PostgreSQL arizonix schema
              (restricted role + RLS + guarded functions)
```

The Next.js App Router application uses `@supabase/ssr` with a per-request server client, browser client, and Next.js 16 proxy. The proxy refreshes cookie-backed sessions; the protected route-group layout independently verifies claims before rendering the research shell. Login, sign-up, email confirmation, check-email, and sign-out are public or server-action boundaries. Return destinations are restricted to local non-auth paths.

The FastAPI application keeps `/api/v1/health` public and protects `/api/v1/me` with an injectable bearer-token verifier. It derives the expected issuer and JWKS URL from a trusted Supabase origin; accepts only RS256 or ES256; verifies signature, issuer, audience, expiry, issued-at time, and UUID subject; and returns only user ID and optional email. Its bounded JWKS cache allows stale known keys during a temporary outage, throttles unknown-key refreshes, and fails closed when trust cannot be established.

The web API client attaches the access token only to the configured Arizonix API origin. A 401 triggers one coordinated refresh and one retry. Workspace requests use the verified subject inside an explicit database transaction. The restricted runtime role reads only RLS-visible rows and invokes guarded mutation functions. No service-role key or privileged migration connection is used for normal requests.

Workspaces have owner, admin, analyst, and viewer memberships. Central application checks provide clear
HTTP semantics, while grants, RLS, guarded functions, and workspace-row locks enforce isolation and the
final-owner invariant at the persistence boundary. See [authorization.md](authorization.md) and
[database.md](database.md).

## Domain and evaluation boundary

The backend now contains version 1.0 framework-independent contracts for companies, research projects
and runs, sources and snapshots, evidence, versioned claims and evidence relationships, and human-review
decisions. These models import no FastAPI, persistence library, collector SDK, or model-provider SDK.
Strict local validation is complemented by an explicit assembled-record validator for references,
workspace/company consistency, conflicting links, and minimum structural support for verified claims.

These future research records remain an in-memory contract boundary; Step 2.2 persists only users,
workspaces, and memberships. No business route exposes the research records. See [domain-model.md](domain-model.md)
for semantics and [the ADR index](adr/README.md) for accepted decisions and implementation status.

The repository-level `evals` directory holds versioned, synthetic, offline cases. Its schema is generated
from the Python evaluation model and checked for drift. Validation establishes fixture integrity only;
no model, agent, accuracy measurement, or behavior evaluator runs.

## Development infrastructure

Direct uv and npm workflows remain the primary development path. Docker Compose contains the API and web application plus an opt-in PostgreSQL `database` profile:

```text
Host browser
  | http://127.0.0.1:${WEB_HOST_PORT}
  v
Web container :3000

Host browser
  | http://127.0.0.1:${API_HOST_PORT}
  v
API container :8000
```

The application containers bind `0.0.0.0` internally, publish to host loopback, run as non-root users, include process-level health checks, and use direct processes that receive shutdown signals. PostgreSQL publishes only to loopback when its profile is selected. No Docker socket, privileged mode, queue, or research provider is present.

The web image is a Next.js standalone production build. `NEXT_PUBLIC_API_BASE_URL` is passed as a build argument because Next.js embeds public variables in browser JavaScript at build time. Browser code cannot resolve the Compose-only hostname `api`, so the value must be a host-reachable origin. Container edits and public configuration changes require a rebuild; hot reload is not part of the Compose workflow.

## Automated verification

GitHub Actions defines three read-only jobs on pushes and pull requests to `main`:

- Backend quality starts disposable PostgreSQL, provisions restricted roles, applies a fresh Alembic migration, then runs Ruff lint, formatting verification, and pytest including real RLS tests.
- Frontend quality installs with `npm ci`, then runs ESLint, Prettier verification, public configuration tests, strict TypeScript, and the production build.
- Browser integration installs Chromium, runs mocked boundary tests, and runs a real API process lifecycle test against the actual frontend.

The workflow cancels superseded runs, uses bounded timeouts and readiness polling, caches package downloads using lockfiles, and uploads browser failure artifacts for three days. It does not use secrets or paid services. The workflow file exists locally; only a GitHub-hosted run can establish that hosted CI passes.

## Planned architecture, not implemented

Future steps may add:

- PostgreSQL tables and RLS for future prospects, evidence, claims, decisions, and audit history. Only the workspace authorization foundation is implemented.
- pgvector for evidence retrieval where semantic similarity is justified.
- Redis and Celery for bounded background work, scheduling, retries, and task visibility.
- LangGraph for explicit, inspectable coordination among specialized analysis and verification agents.
- Source adapters for deterministic collection from allowed websites, search providers, and approved business data sources.
- Provider-independent model adapters with strict structured outputs and evidence-reference validation.
- Version-bound human review followed, only in a later phase, by suppression-aware and idempotent outbound operations.

These technologies are plans only. They are not installed, configured, containerized, or represented as functional.

## Responsibility boundaries

Deterministic code should collect and normalize permitted source material. Evidence storage should preserve source identity, capture time, excerpts, and contradictions. AI analysis should transform evidence into clearly labeled claims, inferences, hypotheses, and unknowns. Independent verification should challenge material conclusions. Human review should remain the authority for opportunity decisions and any outreach approval.

Future controls must include workspace isolation, complete source provenance, crawl restrictions and robots-policy handling, prompt-injection defenses for untrusted content, enforceable time and cost budgets, and explicit human approval before outreach. A finding that no meaningful service problem exists must remain a valid final result.

The requirements-to-roadmap register is currently provisional because the full project proposal is not
present. See [requirements-coverage.md](requirements-coverage.md); planned technologies and controls in
that register are not operational capabilities.
