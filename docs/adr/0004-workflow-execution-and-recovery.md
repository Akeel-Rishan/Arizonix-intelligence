# ADR 0004: Workflow execution and recovery

- **Status:** Accepted; implementation planned
- **Date:** 2026-09-28

## Context

Research is long-running, interruptible, budgeted, and dependent on unreliable external systems. Queue
delivery and worker crashes can cause the same unit of work to run more than once.

## Decision

Plan Celery with Redis for background task delivery and LangGraph for explicit research coordination,
checkpoints, and human interruption. PostgreSQL remains the durable source of business state; queue or
graph memory is not authoritative.

Assume at-least-once delivery. Every side-effecting operation needs an idempotency key, bounded retry
policy, cancellation check, persisted checkpoint, and enforced time/cost/request budget. Do not claim
exactly-once execution.

Task-level retries will own infrastructure failures around a whole task. Graph-node retries will own
bounded semantic/provider attempts inside a running task. A node must not multiply retries already
performed by Celery; the combined attempt budget must be explicit and persisted.

## Alternatives considered

- Synchronous HTTP research: rejected because it cannot reliably survive long jobs or interruption.
- Queue state as business state: rejected because delivery infrastructure is not an audit store.
- Unlimited nested retries: rejected because they multiply cost and hide terminal failures.

## Consequences

Handlers must be replay-safe and expose cancellation/budget boundaries. Recovery favors durable state
over process-local progress and may repeat work while preventing duplicate effects.

## Implementation status and review trigger

Only project/run status contracts exist. Celery, Redis, LangGraph, workers, retries, checkpoints,
cancellation, and budgets are not installed or operational. Review before worker implementation and
after the first failure-recovery exercise.
