# ADR 0003: Evidence provenance and claim semantics

- **Status:** Accepted; initial contracts implemented
- **Date:** 2026-09-28

## Context

A URL, one capture of it, an observation extracted from that capture, and a conclusion are different
things. Collapsing them makes historical inspection, contradiction, freshness, and source independence
impossible to reason about honestly.

## Decision

Represent source identity, immutable source snapshots, evidence observations, versioned claims, and
claim-to-evidence relationships separately. Preserve requested and final URLs, capture outcome,
capture time, content hash, storage reference, and publication precision. Capture time never substitutes
for an unknown publication time.

Treat HTTP availability, temporal freshness, evidence strength, evidentiary classification, and claim
lifecycle as separate dimensions. A retained snapshot can support a qualified historical statement
after its live URL becomes unavailable. An unavailable external article does not mean the client's
website is broken; a currently broken client page is a bounded direct observation. Syndicated copies
are not independent corroboration.

Support, contradiction, and ambiguous relevance are explicit link records. Original captured material
remains distinguishable from observations and interpretations. Scores are optional heuristics until
calibrated and are not probabilities or guarantees.

## Alternatives considered

- One `finding` object: rejected because it overloads source, evidence, interpretation, and status.
- Capture time as publication time: rejected because it fabricates temporal precision.
- Page count as corroboration: rejected because duplicates share an origin.

## Consequences

The model requires more references but supports inspection, history, contradiction, and invalidation.
Verified claims require support links, although references alone do not establish substantive truth.

## Implementation status and review trigger

Version 1.0 contracts and deterministic relationship checks are implemented. Collection, snapshot
storage, substantive verification, trust calibration, and invalidation workflows are not. Review after
real collector data reveals missing provenance or precision needs.
