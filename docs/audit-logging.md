# Audit logging

## Two different records

Arizonix uses two deliberately separate mechanisms:

- **Business audit events** are committed PostgreSQL rows for successful workspace, membership, and company
  changes. They are workspace-scoped and written in the same transaction as the change.
- **Security/operational logs** are structured JSON server logs for missing or invalid authentication,
  inaccessible workspaces, insufficient roles, final-owner protection, authentication-service outages,
  and audit persistence failures. They describe attempts and failures; they are not committed business
  events.

Stdout log retention and durability depend on the hosting environment. No external log service,
monitor, or alert is configured in this step. A rejected request is therefore not claimed to have a
durable PostgreSQL audit record.

## Event catalog and semantics

All events use schema version `1`. Workspace creation creates only `workspace.created`; the initial
owner membership is bootstrap state and does not produce a second event. A rename or role request that
would not change its stored value produces no event. Removal by another authorized member and voluntary
departure are distinct.

| Action                    | Target       | Allowed details                                          |
| ------------------------- | ------------ | -------------------------------------------------------- |
| `workspace.created`       | Workspace ID | `name`                                                   |
| `workspace.renamed`       | Workspace ID | `previous_name`, `new_name`                              |
| `membership.added`        | User ID      | `target_user_id`, `assigned_role`                        |
| `membership.role_changed` | User ID      | `target_user_id`, `previous_role`, `new_role`            |
| `membership.removed`      | User ID      | `target_user_id`, `previous_role`                        |
| `membership.left`         | Actor ID     | `target_user_id`, `previous_role`                        |
| `company.created`         | Company ID   | `name`, `version`                                        |
| `company.updated`         | Company ID   | changed fields, safe transitions, change flags, versions |
| `company.archived`        | Company ID   | `previous_version`, `new_version`                        |
| `company.restored`        | Company ID   | `previous_version`, `new_version`                        |

Synthetic examples:

```json
{
  "action": "workspace.renamed",
  "actor_user_id": "11111111-1111-4111-8111-111111111111",
  "target_id": "22222222-2222-4222-8222-222222222222",
  "details": { "previous_name": "Northstar", "new_name": "Signal Lab" }
}
```

```json
{
  "action": "membership.role_changed",
  "actor_user_id": "11111111-1111-4111-8111-111111111111",
  "target_id": "33333333-3333-4333-8333-333333333333",
  "details": {
    "target_user_id": "33333333-3333-4333-8333-333333333333",
    "previous_role": "analyst",
    "new_role": "viewer"
  }
}
```

The JSON details must be an object and are limited to 4096 bytes. The audit record stores stable IDs,
not mutable email addresses. A departed actor is displayed by stable user ID when no suitable display
information is available. Names stored as before/after values preserve the meaning of that event even
after later renames.

Company update events may include before/after values only for name, industry, and country. Website,
description, and notes changes are represented by booleans; their values are excluded so URL query
secrets and free text are not copied into audit history.

## Atomicity and database boundary

The existing guarded mutation functions are the sole authoritative business-event writer. The runtime
role cannot directly modify workspace data, and its only mutation paths are those functions. Each
function derives the actor from transaction-local verified identity, obtains workspace/target values
from affected records, performs the change, then invokes an internal audit writer. It does not accept
an actor from the request body.

The audit insert and business mutation share one PostgreSQL transaction:

- commit preserves both;
- rollback preserves neither;
- a required audit failure raises `AR007` and rolls back the mutation;
- related operations inside one request share the server-generated request UUID.

`arizonix_runtime` has `SELECT` only on `audit_events`; row-level security exposes rows only when its
transaction actor is a current owner/admin. It cannot directly `INSERT`, `UPDATE`, `DELETE`, or
`TRUNCATE`, execute the internal writer, disable table triggers, or alter owner functions/policies.
`PUBLIC` and Supabase database roles receive no access. The security-definer functions use the
non-login `arizonix_owner`, an empty `search_path`, schema-qualified static SQL, and revoked default
execution.

This is **append-only against the application runtime role**, not cryptographic tamper-proofing against
database administrators or a compromised migration credential.

## Reading and correlation

Owners and admins may use Settings → Audit history or the read-only endpoints:

- `GET /api/v1/workspaces/{workspace_id}/audit-events`
- `GET /api/v1/workspaces/{workspace_id}/audit-events/{event_id}`

Analysts/viewers receive 403. Non-members and cross-workspace event IDs receive 404. Lists use stable
`occurred_at DESC, id DESC` cursor pagination, a page size of 1–100, optional action/actor filters, and
an optional paired UTC date range capped at 366 days. Responses are `private, no-store` and omit totals
and global-profile joins.

The API generates a UUID for every request, returns it as `X-Request-ID`, and sets it in the same local
database transaction as the verified actor. Client-supplied correlation headers are not trusted. Local
settings expire at commit/rollback so pooled connections cannot inherit identity or correlation state.
Maintenance calls to audited mutation functions must establish both a real actor and request UUID;
missing context fails instead of inventing an actor.

## Sensitive-data exclusions

Audit details and application security logs never intentionally contain passwords, access/refresh
tokens, authorization headers, cookies, API keys, connection strings, confirmation tokens, request
bodies, arbitrary user metadata, IP addresses, or user-agent strings. Uvicorn access logging strips
query strings. Operational reason codes are fixed values so attacker-controlled text cannot inject log
lines, and an unverified token subject is never called a verified actor.

## Retention and deletion

No automatic retention or destructive deletion policy exists yet. Audit references use restrictive
foreign keys rather than membership cascades, so removing a membership preserves history. A future
user/workspace erasure or retention feature must explicitly define legal retention, anonymization,
referential behavior, exports, and administrator auditability before destructive deletion is added.

## Troubleshooting

- `audit_persistence_failed` / HTTP 500: the required audit insert failed, so the business mutation was
  rolled back. Use the response `X-Request-ID` to correlate the structured server log, then inspect
  migration state, constraints, storage availability, and object ownership with migration credentials.
- 403 when reading history: the verified user is still a member but is not currently owner/admin.
- 404 when reading history: the workspace is inaccessible or the event does not belong to that
  workspace.
- Empty history after upgrade: only mutations committed after the audit migration are captured; this
  migration does not fabricate historical events.
- Do not grant runtime DML or internal-writer execution to repair an incident. Correct the migration or
  database condition through the privileged operational process, then retry the original mutation.
