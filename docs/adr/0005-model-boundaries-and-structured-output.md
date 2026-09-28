# ADR 0005: Model boundaries and structured output

- **Status:** Accepted; implementation planned
- **Date:** 2026-09-28

## Context

Model providers change, model output is probabilistic, and captured web content may contain prompt
injection. Provider responses cannot directly establish evidence, authorization, or side effects.

## Decision

Introduce a provider-independent model interface when model work begins. Requests will identify a
versioned prompt, model configuration, budget, and expected structured-output schema. Responses must
pass strict structural validation and deterministic checks that every evidence reference exists and
belongs to the correct workspace, company, and claim version.

Treat external content as untrusted data, never operational instructions. Deterministic code enforces
hard constraints, authorization, budgets, allowed actions, and reference integrity. Store concise
decision summaries, prompt/model versions, inputs by reference, outputs, and provenance needed for
audit; do not require or expose private model chain-of-thought.

## Alternatives considered

- Provider SDK types in the domain: rejected because they prevent replacement and contaminate contracts.
- Free-form text as authoritative output: rejected because hard constraints cannot be enforced reliably.
- Model self-validation alone: rejected because the same probabilistic component cannot enforce policy.

## Consequences

Adapters may lose provider-specific features unless deliberately exposed. Schema and prompt changes
need versions and evaluation. Valid structure still does not guarantee a correct conclusion.

## Implementation status and review trigger

No model provider, prompt runtime, agent, or behavior evaluator exists. Domain and evaluation schemas
establish future boundaries only. Review when selecting the first provider and on every breaking output
schema change.
