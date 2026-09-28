# Architecture decision records

ADRs record durable choices, their trade-offs, and whether their controls exist today. A status of
**Accepted** means the direction is agreed; it does not mean every planned component is operational.

| ADR                                                     | Decision                                | Status                           |
| ------------------------------------------------------- | --------------------------------------- | -------------------------------- |
| [0001](0001-monorepo-and-module-boundaries.md)          | Monorepo and module boundaries          | Accepted                         |
| [0002](0002-persistence-and-workspace-isolation.md)     | Persistence and workspace isolation     | Accepted, planned implementation |
| [0003](0003-evidence-provenance-and-claim-semantics.md) | Evidence provenance and claim semantics | Accepted, contracts implemented  |
| [0004](0004-workflow-execution-and-recovery.md)         | Workflow execution and recovery         | Accepted, planned implementation |
| [0005](0005-model-boundaries-and-structured-output.md)  | Model boundaries and structured output  | Accepted, planned implementation |
| [0006](0006-human-approval-and-outreach.md)             | Human approval and outreach             | Accepted, review contract only   |

New decisions receive the next four-digit number. Accepted ADRs are superseded by a new ADR rather
than silently rewritten; factual implementation-status updates may be appended.
