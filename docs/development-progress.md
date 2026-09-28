# Development progress

## Step status

- Step 1.1: **user-verified**
- Step 1.2: **user-verified**
- Step 1.3: **awaiting user verification**

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

## Next planned step

Step 2.1: Supabase authentication and protected routes.

Step 2.1 has not been implemented.
