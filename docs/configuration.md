# Configuration

## Configuration contract

| Name                       | Purpose and allowed values                                     | Default                 | Visibility                             | Read time                 |
| -------------------------- | -------------------------------------------------------------- | ----------------------- | -------------------------------------- | ------------------------- |
| `ARIZONIX_APP_ENVIRONMENT` | API environment: `development`, `test`, or `production`        | `development`           | Server-only                            | API startup               |
| `ARIZONIX_APP_VERSION`     | Non-empty version returned by health and OpenAPI metadata      | `0.1.0`                 | Server response includes version       | API startup               |
| `ARIZONIX_LOG_LEVEL`       | `debug`, `info`, `warning`, `error`, or `critical`             | `info`                  | Server-only                            | API startup               |
| `ARIZONIX_ALLOWED_ORIGINS` | Comma-separated or JSON array of exact HTTP(S) browser origins | Local ports 3000        | Server-only                            | API startup               |
| `NEXT_PUBLIC_API_BASE_URL` | HTTP(S) origin of the API, without `/api/v1` or another path   | `http://127.0.0.1:8000` | Public, embedded in browser JavaScript | Next.js build/dev startup |
| `API_HOST_PORT`            | Host loopback port published by Compose for the API            | `8000`                  | Local Compose setting                  | Compose interpolation     |
| `WEB_HOST_PORT`            | Host loopback port published by Compose for the web app        | `3000`                  | Local Compose setting                  | Compose interpolation     |

No listed value is a secret. Never place credentials or private keys in a `NEXT_PUBLIC_` variable because Next.js embeds it into the browser bundle.

The public API convention is origin-only. The client owns the `/api/v1/health` path. Rejecting path-bearing base URLs prevents accidental requests such as `/api/v1/api/v1/health`.

## Files and ownership

- `apps/api/.env.example` documents direct API defaults. Copy it to ignored `apps/api/.env` for direct development.
- `apps/web/.env.example` documents the browser-visible Next.js value. Copy it to ignored `apps/web/.env.local` for direct development.
- Root `.env.example` documents Compose interpolation. Copy it to ignored root `.env` only when using Compose.
- `compose.yaml` explicitly passes server settings to the API and passes the public API origin as a web image build argument.

These files serve different launch modes and do not automatically override one another.

## Precedence

For direct API development, Pydantic Settings resolves process environment variables first, then `apps/api/.env`, then code defaults. Tests pass `_env_file=None` and explicitly isolate relevant process variables, so a developer file cannot change test outcomes.

For direct Next.js development and builds, Next.js uses its documented order: process environment, environment-specific local file, `.env.local`, environment-specific file, then `.env`. `NEXT_PUBLIC_API_BASE_URL` is frozen into browser JavaScript when Next.js builds.

For Compose interpolation, shell variables override values in root `.env`, which override the `${NAME:-default}` values in `compose.yaml`. Compose then passes only the explicitly declared API variables. The web setting is a build argument, not a runtime override.

Changing `NEXT_PUBLIC_API_BASE_URL` after an image is built does not modify its JavaScript. Rebuild the web image.

## Port-change example

To expose the web app on 4000 and the API on 9000, set these values in root `.env`:

```dotenv
API_HOST_PORT=9000
WEB_HOST_PORT=4000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:9000
ARIZONIX_ALLOWED_ORIGINS=http://127.0.0.1:4000,http://localhost:4000
```

Then rebuild because the public API URL is build-time configuration:

```powershell
docker compose up --build --force-recreate --wait
```

The browser must use a host-reachable address. `http://api:8000` works only between containers and must not be used for `NEXT_PUBLIC_API_BASE_URL`.

## Validation behavior

The backend rejects unknown environments, unknown log levels, blank versions, wildcard CORS, empty origin lists, credentials, malformed ports, and origins containing paths, queries, or fragments. Startup fails with Pydantic field-level validation details.

The frontend accepts only HTTP(S) origins and normalizes one trailing slash through URL origin parsing. Invalid public configuration produces a concise health-card correction and no health request. Raw exceptions, environment contents, and secrets are not displayed.
