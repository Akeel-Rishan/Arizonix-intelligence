# Workspace authorization

## Permission matrix

Every protected operation reloads the actor's current membership. Supabase profile metadata is never a
source of authorization, unknown roles fail validation, and no membership means no access.

| Operation                                 | Owner                           | Admin | Analyst | Viewer |
| ----------------------------------------- | ------------------------------- | ----- | ------- | ------ |
| Read workspace and member list            | Yes                             | Yes   | Yes     | Yes    |
| Rename workspace                          | Yes                             | Yes   | No      | No     |
| Add owner or admin                        | Yes                             | No    | No      | No     |
| Add analyst or viewer                     | Yes                             | Yes   | No      | No     |
| Change any member role                    | Yes, subject to last-owner rule | No    | No      | No     |
| Change analyst/viewer between those roles | Yes                             | Yes   | No      | No     |
| Remove owner or admin                     | Yes, subject to last-owner rule | No    | No      | No     |
| Remove analyst or viewer                  | Yes                             | Yes   | No      | No     |
| Leave workspace                           | Yes, unless last owner          | Yes   | Yes     | Yes    |

An owner transfers practical ownership by promoting another member before leaving or demoting the old
owner. A workspace row is locked during add, role-change, remove, and leave operations. The final-owner
check and mutation therefore occur in one serialized transaction even under concurrent requests.

## Identity and enforcement flow

```text
Supabase access JWT
  -> FastAPI verifies signature, issuer, audience, time claims, and UUID subject
  -> API opens an explicit database transaction
  -> set_config('arizonix.user_id', verified subject, true)
  -> profile is provisioned from the verified subject/email
  -> application permission check
  -> RLS policy and/or guarded mutation function checks the same transaction-local identity
  -> commit or rollback clears the local setting before the pooled connection is reused
```

The browser cannot submit the actor identity. Body `user_id` exists only where an exact target existing
user is required. Workspace IDs select a resource but never establish access. Inaccessible workspace
IDs return 404, known members without an administrative permission receive 403, and duplicate or
last-owner conflicts receive controlled 409 responses.

Transaction-local context is not JWT verification: the API performs cryptographic verification first.
It protects against omitted tenant filters and prevents identity leakage between pooled requests. It
does not protect against a compromised backend process that holds the runtime database password.

## Database boundary

Application tables live in the unexposed `arizonix` schema. `anon`, `authenticated`, and `PUBLIC` have
no schema, table, or function privileges. `arizonix_runtime` is a non-owner, non-superuser role without
`BYPASSRLS`, database/schema creation, role creation, or membership in the object-owner role. It can
select RLS-filtered rows and execute an explicit allowlist of functions; it has no direct DML grants.

Mutation functions run as the non-login `arizonix_owner`, set an empty `search_path`, use qualified
objects and static SQL, validate the transaction actor, and expose only one business operation each.
Default `PUBLIC` execution is revoked. The owner deliberately relies on PostgreSQL's table-owner RLS
bypass inside these guarded functions, so `FORCE ROW LEVEL SECURITY` is not enabled. The owner cannot
log in, while the normal runtime role remains subject to RLS. This is the controlled elevated path that
solves atomic workspace/first-owner creation and avoids recursive membership policies.

## Existing-user membership flow

An authenticated request provisions a minimal `application_users` row whose UUID matches the verified
Supabase subject. Email is display-only profile data and is never an authorization key. An owner/admin
adds an existing user using the exact UUID shown in that user's Account card; there is no global search,
auth-account creation, or invitation. A disabled/deleted Supabase account cannot obtain a valid token,
but automatic profile cleanup is deferred.

Invitations, email delivery, business-data permissions, and the full audit log remain deferred. Step
2.3 adds audit logging and deeper authorization testing without changing this matrix silently.
