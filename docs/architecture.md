# Architecture

## Current foundation

Step 1.1 contains two independently started local applications:

```text
Browser at 127.0.0.1:3000
        |
        | GET /api/v1/health
        v
FastAPI at 127.0.0.1:8000
```

The Next.js App Router application renders the research shell and keeps interactivity in two client-side leaves: route-aware navigation and the API health card. The health client reads the public `NEXT_PUBLIC_API_BASE_URL`, applies a bounded timeout and cancellation, validates the response contract, and does not poll.

The FastAPI application is created through `create_app`, loads typed settings through Pydantic Settings, and exposes one versioned liveness endpoint. CORS grants only configured local origins, `GET`, and the headers needed for this unauthenticated request. The endpoint has no external dependencies and intentionally says nothing about future readiness.

No data store, queue, agent, source adapter, provider account, or authentication system exists in the current implementation.

## Planned architecture, not currently working

Future steps are expected to add these roles incrementally:

- Supabase/PostgreSQL for workspace-scoped operational records, evidence, claims, decisions, and audit history.
- pgvector for evidence retrieval where semantic similarity is justified.
- Redis and Celery for bounded background work, scheduling, retries, and task visibility.
- LangGraph for explicit, inspectable coordination among specialized analysis and verification agents.
- Source adapters for deterministic collection from allowed websites, search providers, and approved business data sources.

These technologies are plans only. They are not installed, configured, or represented as functional in Step 1.1.

## Responsibility boundaries

Deterministic code should collect and normalize permitted source material. Evidence storage should preserve source identity, capture time, excerpts, and contradictions. AI analysis should transform evidence into clearly labeled claims, inferences, hypotheses, and unknowns. Independent verification should challenge material conclusions. Human review should remain the authority for opportunity decisions and any outreach approval.

Future controls must include workspace isolation, complete source provenance, crawl restrictions and robots-policy handling, prompt-injection defenses for untrusted content, enforceable time and cost budgets, and explicit human approval before outreach. A finding that no meaningful service problem exists must remain a valid final result.

