# Requirements coverage

## Source status

No full project proposal or numbered roadmap was found in the repository on 2026-09-28. The only local
proposal reference was the Step 1.3 line in `docs/development-progress.md`. This register is therefore
**provisional**, derived from the Step 1.3 brief, and does not claim complete proposal coverage.

Add the authoritative, unchanged proposal at `docs/project-proposal.md`. A later review should replace
the “Step 1.3 brief” references with its actual section numbers/titles and reconcile the provisional
coverage IDs. The IDs below identify register rows; they are not invented proposal numbering.

The agreed build sequence is: foundation → identity/access → prospect management → evidence → workers
→ source collection → core agents → specialist research → problem discovery → verification →
opportunities → human review → outreach → discovery → production → advanced capabilities. Only Step
2.1, Supabase authentication and protected routes, has an exact future step number in the available
source; other future step numbers remain TBD rather than fabricated.

| ID      | Proposal reference       | Requirement summary                                                  | Planned phase / step                     | Owner                       | Acceptance evidence                                                 | Status                      |
| ------- | ------------------------ | -------------------------------------------------------------------- | ---------------------------------------- | --------------------------- | ------------------------------------------------------------------- | --------------------------- |
| COV-001 | Step 1.3 brief §F        | Company discovery and configurable SMB qualification                 | Discovery / step TBD                     | Discovery boundary          | Qualification rules and discovery tests                             | Planned                     |
| COV-002 | Step 1.3 brief §F        | Company/person identity resolution and duplicate prevention          | Prospect management / step TBD           | Identity + prospect modules | Same-name and duplicate fixtures; uniqueness tests                  | Partially implemented       |
| COV-003 | Step 1.3 brief §F        | Company and website research                                         | Source collection / step TBD             | Collector adapters          | Allowed-source integration tests and snapshots                      | Planned                     |
| COV-004 | Step 1.3 brief §F        | Customer and decision-maker research                                 | Specialist research / step TBD           | Customer/person boundaries  | Attributed, identity-resolved evidence                              | Deferred                    |
| COV-005 | Step 1.3 brief §F        | Social, technology, competitor, and process research                 | Specialist research / step TBD           | Specialist adapters         | Per-source fixtures and provenance tests                            | Deferred                    |
| COV-006 | Step 1.3 brief §F        | Positive and negative customer patterns                              | Specialist research / step TBD           | Customer analysis           | Balanced-pattern evaluation cases                                   | Planned                     |
| COV-007 | Step 1.3 brief §F        | Evidence, snapshots, provenance, temporal validity, and source trust | Evidence / step TBD                      | Domain + evidence boundary  | Contract/schema tests and fixture integrity                         | Partially implemented       |
| COV-008 | Step 1.3 brief §F        | Independent corroboration and syndicated-copy handling               | Verification / step TBD                  | Verification boundary       | Duplicate-source and corroboration evaluations                      | Partially implemented       |
| COV-009 | Step 1.3 brief §F        | Claims, versions/history, contradiction links, and invalidation      | Evidence / step TBD                      | Claims boundary             | Relationship and verified-claim negative tests                      | Partially implemented       |
| COV-010 | Step 1.3 brief §F        | Hybrid relational, lexical, and semantic retrieval                   | Evidence / step TBD                      | Retrieval boundary          | Retrieval relevance and provenance tests                            | Planned                     |
| COV-011 | Step 1.3 brief §F        | Pain points, root causes, and adaptive questions                     | Problem discovery / step TBD             | Analysis boundary           | Evidence-bound problem cases                                        | Planned                     |
| COV-012 | Step 1.3 brief §F        | Stopping conditions, including no problem and insufficient evidence  | Problem discovery / step TBD             | Workflow + analysis         | Terminal outcome fixtures                                           | Partially implemented       |
| COV-013 | Step 1.3 brief §F        | Contradiction search and skeptical independent review                | Verification / step TBD                  | Verification boundary       | Adversarial contradiction suite                                     | Planned                     |
| COV-014 | Step 1.3 brief §F        | Capabilities, opportunities, and solution comparisons                | Opportunities / step TBD                 | Opportunity boundary        | Ranked alternatives with evidence                                   | Deferred                    |
| COV-015 | Step 1.3 brief §F        | Financial assumptions separated from facts                           | Opportunities / step TBD                 | Opportunity boundary        | Unsupported-estimate fixture and assumption records                 | Partially implemented       |
| COV-016 | Step 1.3 brief §F        | Confidence, completeness, opportunity scoring, and calibration       | Verification + opportunities / step TBD  | Evaluation boundary         | Calibrated held-out metrics; no uncalibrated probability claims     | Planned                     |
| COV-017 | Step 1.3 brief §F        | Budgets, caching, retries, checkpoints, and job recovery             | Workers / step TBD                       | Celery/LangGraph boundary   | Recovery, idempotency, cancellation, and budget tests               | Planned                     |
| COV-018 | Step 1.3 brief §F        | Tracing, prompt versions, and model configuration                    | Core agents / step TBD                   | Model boundary              | Versioned run provenance and redacted traces                        | Planned                     |
| COV-019 | Step 1.3 brief §F        | Dashboard modules, timelines, and evidence inspection                | Human review / step TBD                  | Next.js presentation        | Accessible end-to-end review tasks                                  | Planned                     |
| COV-020 | Step 1.3 brief §F        | Human controls and artifact-version approval                         | Human review / step TBD                  | Review boundary             | Version invalidation and authorization tests                        | Partially implemented       |
| COV-021 | Step 1.3 brief §F        | Authentication, protected routes, and workspace isolation            | Identity/access / Step 2.1               | Auth + database boundaries  | Route, policy, cross-tenant, and privileged-path tests              | Planned                     |
| COV-022 | Step 1.3 brief §F        | Roles, secrets, and audit logging                                    | Identity/access + production / steps TBD | Security boundary           | RBAC matrix, secret scan, immutable audit events                    | Planned                     |
| COV-023 | Step 1.3 brief §F        | Privacy, retention, permitted access, and suppression                | Production + outreach / steps TBD        | Governance boundary         | Retention/access/suppression policy tests                           | Planned                     |
| COV-024 | Step 1.3 brief §F        | Outreach-reference safety and draft approval                         | Outreach / step TBD                      | Outbound boundary           | Exact-reference and versioned-approval tests                        | Planned                     |
| COV-025 | Step 1.3 brief §F        | Explicit sending and response tracking                               | Outreach / step TBD                      | Outbound integrations       | Suppression, authorization, idempotency, and sandbox delivery tests | Deferred                    |
| COV-026 | Step 1.3 brief §F        | Evaluation metrics and adversarial scenarios                         | Cross-phase                              | Evaluation boundary         | Actual-output evaluator and published rubric                        | Partially implemented       |
| COV-027 | Step 1.3 brief §F        | Production deployment, backups, monitoring, and recovery             | Production / step TBD                    | Operations                  | Restore drill, alerts, SLOs, and runbooks                           | Planned                     |
| COV-028 | Step 1.3 brief §F        | Refresh monitoring, industry packs, and outcome analysis             | Advanced capabilities / step TBD         | Advanced modules            | Longitudinal and domain-pack evaluations                            | Deferred                    |
| COV-029 | Source audit requirement | Verify this map against the authoritative full proposal              | Foundation follow-up                     | Documentation               | Reviewed proposal-to-row reconciliation                             | Needs proposal verification |

“Partially implemented” means a contract, ADR, or deterministic fixture exists; it does not mean an
operational business capability exists. ADR-only items are not marked implemented.
