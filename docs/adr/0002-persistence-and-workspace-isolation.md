# ADR 0002: Persistence and workspace isolation

- **Status:** Accepted; implementation planned
- **Date:** 2026-09-28

## Context

Evidence relationships need transactional integrity, source snapshots need durable immutable storage,
and every tenant-owned record must remain isolated. Semantic retrieval may help later but must not
replace explicit provenance links.

## Decision

Plan PostgreSQL through Supabase for relational operational state, object storage for captured source
material, and pgvector only where semantic retrieval is justified. Begin with relational IDs for
source, snapshot, evidence, claim, contradiction, and review relationships.

Every workspace-owned record carries `workspace_id`; company-owned records also carry `company_id`.
Application authorization and database isolation policies will both be tested. Row-level security is
defense in depth, not a substitute for application authorization: privileged/service connections can
bypass RLS and must be narrowly controlled. Migrations, constraints, policies, and storage rules arrive
with persistence work.

## Alternatives considered

- Vector-only evidence storage: rejected because similarity is not provenance or referential integrity.
- Object storage for all state: rejected because relationships and reviews require transactions.
- RLS as the sole authorization control: rejected because privileged connections can bypass it.

## Consequences

Workspace identity is explicit in current contracts, but IDs and Pydantic validation do not authorize
access. Future migrations need foreign keys, uniqueness rules, policy tests, and privileged-path tests.

## Implementation status and review trigger

Only in-memory contracts and cross-record validation exist. No database, Supabase client, bucket,
migration, pgvector extension, RLS policy, or authorization implementation exists. Review during Step
2.1 and again before the first persistence migration.
