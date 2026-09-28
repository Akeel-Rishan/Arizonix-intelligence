# Architecture

## Implemented foundation

Arizonix Intelligence currently consists of two independently deployable applications:

```text
Browser at 127.0.0.1:3000
        |
        | GET {public API origin}/api/v1/health
        v
FastAPI at 127.0.0.1:8000
```

The Next.js App Router application renders the research shell and limits client-side interactivity to route-aware navigation and the API health card. Its configuration module validates one browser-visible API origin. The typed health client adds the versioned path, applies a bounded timeout and cancellation, validates the response contract, and does not poll.

The FastAPI application uses an injectable application factory and Pydantic Settings. It exposes one versioned liveness endpoint, with explicit environment, version, log-level, and CORS configuration. The endpoint remains independent of databases, workers, and providers and does not imply their readiness.

## Domain and evaluation boundary

The backend now contains version 1.0 framework-independent contracts for companies, research projects
and runs, sources and snapshots, evidence, versioned claims and evidence relationships, and human-review
decisions. These models import no FastAPI, persistence library, collector SDK, or model-provider SDK.
Strict local validation is complemented by an explicit assembled-record validator for references,
workspace/company consistency, conflicting links, and minimum structural support for verified claims.

This is an in-memory contract boundary, not a persistence or authorization layer. No business route
exposes these records, and no database model or migration exists. See [domain-model.md](domain-model.md)
for semantics and [the ADR index](adr/README.md) for accepted decisions and implementation status.

The repository-level `evals` directory holds versioned, synthetic, offline cases. Its schema is generated
from the Python evaluation model and checked for drift. Validation establishes fixture integrity only;
no model, agent, accuracy measurement, or behavior evaluator runs.

## Development infrastructure

Direct uv and npm workflows remain the primary development path. Docker Compose is optional and contains only the API and web application:

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

Both containers bind `0.0.0.0` internally, publish to host loopback, run as non-root users, include process-level health checks, and use direct processes that receive shutdown signals. No Docker socket, privileged mode, database, queue, or provider is present.

The web image is a Next.js standalone production build. `NEXT_PUBLIC_API_BASE_URL` is passed as a build argument because Next.js embeds public variables in browser JavaScript at build time. Browser code cannot resolve the Compose-only hostname `api`, so the value must be a host-reachable origin. Container edits and public configuration changes require a rebuild; hot reload is not part of the Compose workflow.

## Automated verification

GitHub Actions defines three read-only jobs on pushes and pull requests to `main`:

- Backend quality installs with the frozen uv lockfile, then runs Ruff lint, Ruff formatting verification, and pytest.
- Frontend quality installs with `npm ci`, then runs ESLint, Prettier verification, public configuration tests, strict TypeScript, and the production build.
- Browser integration installs Chromium, runs mocked boundary tests, and runs a real API process lifecycle test against the actual frontend.

The workflow cancels superseded runs, uses bounded timeouts and readiness polling, caches package downloads using lockfiles, and uploads browser failure artifacts for three days. It does not use secrets or paid services. The workflow file exists locally; only a GitHub-hosted run can establish that hosted CI passes.

## Planned architecture, not implemented

Future steps may add:

- Supabase/PostgreSQL for workspace-scoped operational records, evidence, claims, decisions, and audit history.
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
