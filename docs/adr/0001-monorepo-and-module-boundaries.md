# ADR 0001: Monorepo and module boundaries

- **Status:** Accepted
- **Date:** 2026-09-28

## Context

The platform needs presentation, business APIs, deterministic source collection, model-assisted
analysis, evidence verification, and consequential outbound actions. Splitting deployment units too
early would add distributed coordination before the domain is stable; combining every concern would
make provenance and authority boundaries difficult to enforce.

## Decision

Keep the Next.js presentation application and FastAPI business API in one repository. Next.js owns
presentation and browser interaction. FastAPI owns business APIs. Core domain contracts stay free of
web frameworks, database libraries, model-provider SDKs, and collector SDKs.

Within the backend, source collection, AI analysis, evidence/claims, independent verification, and
outbound communication are separate module boundaries. Begin as a modular application and extract a
service only after operational or scaling evidence justifies it.

## Alternatives considered

- Premature microservices: rejected because distributed state and deployment cost exceed current need.
- A Next.js-only full-stack application: rejected because Python owns the planned research ecosystem.
- Shared provider/database objects as domain models: rejected because they couple core meaning to vendors.

## Consequences

Contracts can be tested offline and reused by future API, worker, and evaluation adapters. Boundaries
require discipline inside one process; repository proximity does not permit bypassing them.

## Implementation status and review trigger

The two applications and framework-independent domain package exist. Collector, analysis,
verification, and outbound implementations do not. Review when a boundary needs independent scaling,
security isolation, ownership, or release cadence.
