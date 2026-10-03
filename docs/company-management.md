# Company management

Step 3.1 adds manually entered company records under **Prospects**. These workspace-scoped intake
records are not verified identities or evidence. Supplied names, websites, industries, countries,
descriptions, and notes remain unverified until later research attaches sources and resolves identity.

## Data and validation

Each company has an immutable UUID and `workspace_id`, editable name, optional HTTP/HTTPS website,
industry, two-letter country code, description and private workspace notes, creator/updater metadata,
archive metadata, timestamps, and an integer version. Blank optional text becomes `null`. Names are
trimmed and required. URLs require an explicit HTTP or HTTPS scheme and reject credentials, whitespace,
and malformed ports. Create payloads cannot set IDs, ownership, actor metadata, lifecycle metadata,
timestamps, or versions.

| Field          |            Limit |
| -------------- | ---------------: |
| `name`         |   200 characters |
| `website_url`  | 2,048 characters |
| `industry`     |   100 characters |
| `country_code` |  2 ASCII letters |
| `description`  | 2,000 characters |
| `notes`        | 5,000 characters |

The country field validates the storage format (two ASCII letters, normalized uppercase); it does not
claim geopolitical or address verification. Website validation is syntactic only: it performs no
network request, does not prove control, and does not infer a canonical company identity.

Archive is reversible. There is no hard-delete endpoint. Active lists exclude archived rows by
default; `archive=archived` and `archive=all` are explicit alternatives.

## API

All endpoints require a verified bearer identity and current membership in `{workspace_id}`:

| Method  | Path                                                               | Purpose                     |
| ------- | ------------------------------------------------------------------ | --------------------------- |
| `POST`  | `/api/v1/workspaces/{workspace_id}/companies`                      | Create; returns 201         |
| `GET`   | `/api/v1/workspaces/{workspace_id}/companies`                      | Cursor list without notes   |
| `GET`   | `/api/v1/workspaces/{workspace_id}/companies/{company_id}`         | Full detail including notes |
| `PATCH` | `/api/v1/workspaces/{workspace_id}/companies/{company_id}`         | Partial edit                |
| `POST`  | `/api/v1/workspaces/{workspace_id}/companies/{company_id}/archive` | Archive                     |
| `POST`  | `/api/v1/workspaces/{workspace_id}/companies/{company_id}/restore` | Restore                     |

List parameters are `limit` (1–100), opaque `cursor`, `archive`, bounded literal `search`, exact
case-insensitive `industry`, and uppercase `country_code`. Ordering is stable: `created_at DESC, id
DESC`. Cursors are bound to their filter combination. There is deliberately no total count.

An example create body is:

```json
{
  "name": "Example Logistics",
  "website_url": "https://example.test/about",
  "industry": "Logistics",
  "country_code": "LK",
  "description": null,
  "notes": "Review after qualification."
}
```

An edit or lifecycle request uses the version last read, for example
`{"expected_version": 3, "industry": null}` or `{"expected_version": 3}`. New rows inserted while a
user is paging sort ahead of the current cursor and therefore appear after a fresh list reload; stable
tuple pagination avoids shifting offsets and duplicate rows from concurrent additions.

PATCH distinguishes omission from explicit `null`. It requires `expected_version`; archive and restore
require the same. The database locks the row and compares versions atomically. A stale client gets 409
and must reload. A true no-op at the current version creates neither a new version nor an audit event.
Archived records reject edits until restored.

## Authorization and persistence

Owners, admins, and analysts can create, edit, archive, and restore. Viewers can list and read. The UI
hides unavailable controls, FastAPI checks current membership, and PostgreSQL independently enforces
RLS plus role checks inside narrowly granted `SECURITY DEFINER` functions. The runtime role has
RLS-filtered `SELECT`, no table DML, and only the company mutation functions in its execute allowlist.
Cross-workspace IDs do not disclose records.

Company actor references point to durable application-user profiles, not memberships, so membership
removal preserves history. Workspaces and application users cannot be deleted while companies refer
to them.

Successful changes atomically emit `company.created`, `company.updated`, `company.archived`, or
`company.restored`. Update events include changed field names, safe name/industry/country transitions,
version transitions, and booleans for website/description/notes changes. They never copy notes,
description text, or website values/query strings into audit details.

## Apply and verify

After checking the target privileged connection, run from `apps/api`:

```powershell
uv run alembic upgrade head
```

Restart the API, then use `/prospects`. To exercise real database tests against an approved disposable
or test database:

```powershell
$env:ARIZONIX_TEST_MIGRATION_DATABASE_URL=$env:ARIZONIX_MIGRATION_DATABASE_URL
$env:ARIZONIX_TEST_RUNTIME_DATABASE_URL=$env:ARIZONIX_DATABASE_URL
uv run pytest -m postgres
```

Step 3.2 remains separate: locations, canonical domains, duplicate detection, and entity resolution
are not implemented here.
