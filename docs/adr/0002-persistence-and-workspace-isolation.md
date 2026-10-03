# ADR 0002: Persistence and workspace isolation

- **Status:** Accepted; workspace foundation implemented
- **Date:** 2026-09-28

## Context

Evidence relationships need transactional integrity, source snapshots need durable immutable storage,
and every tenant-owned record must remain isolated. Semantic retrieval may help later but must not
replace explicit provenance links.

## Decision

Use PostgreSQL through Supabase for relational operational state, object storage for captured source
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

## Implemented workspace slice

Step 2.2 implements SQLAlchemy async access, Alembic, minimal users/workspaces/memberships, a restricted
runtime role, transaction-local verified identity, application permission checks, RLS reads, and
guarded database mutations. Application tables remain outside the exposed API schema. A non-login
owner provides the narrowly controlled RLS-bypassing function boundary; normal runtime credentials
cannot bypass RLS or write tables directly. Workspace row locks serialize last-owner changes.

Step 2.3 extends this slice with workspace-scoped audit events written atomically by the guarded
mutation functions. The runtime role cannot fabricate or mutate audit rows, while owner/admin RLS
controls reads. See [../audit-logging.md](../audit-logging.md) for guarantees and limitations.

Object storage, pgvector, prospect/research tables, and invitation delivery remain unimplemented.
Review this ADR when the first business-data table is added so its policy follows the same identity and
workspace boundary.
