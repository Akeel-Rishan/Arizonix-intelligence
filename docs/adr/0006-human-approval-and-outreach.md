# ADR 0006: Human approval and outreach

- **Status:** Accepted; review contract implemented, sending planned
- **Date:** 2026-09-28

## Context

Research acceptance and sending a message have different consequences. A generic approval flag can
become stale after evidence, recipient, or content changes and cannot safely authorize an external act.

## Decision

Represent research review and outbound-message approval as separate review scopes. Bind each decision
to an exact artifact ID and version, actor, timestamp, and decision. Relevant edits or evidence
invalidation require reconsideration and a new decision.

Before any future send, deterministic code must verify the exact approved message version, recipient,
current suppression state, actor/workspace authorization, and an idempotency key. Agent-generated text
or recommendations cannot authorize sending. Research approval never implies message-send approval.

## Alternatives considered

- One approval for the entire workflow: rejected because its scope becomes ambiguous after edits.
- Approval bound only to a company: rejected because it cannot identify the reviewed artifact.
- Agent-authorized sending: rejected because generated content cannot grant consequential authority.

## Consequences

Edits deliberately create review friction and preserve a clear audit boundary. Future send code must
fail closed when approval, suppression, authorization, recipient, or version checks disagree.

## Implementation status and review trigger

The versioned human-review decision contract exists. There are no review APIs, users, roles, message
contracts, suppression store, integrations, or send operations. Review before outbound drafts are
introduced and before enabling any external communication.
