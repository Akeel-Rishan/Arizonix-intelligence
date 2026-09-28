# Configuration

## Configuration contract

| Name                                              | Purpose and allowed values                                         | Default                  | Visibility                             | Read time                 |
| ------------------------------------------------- | ------------------------------------------------------------------ | ------------------------ | -------------------------------------- | ------------------------- |
| `ARIZONIX_APP_ENVIRONMENT`                        | API environment: `development`, `test`, or `production`            | `development`            | Server-only                            | API startup               |
| `ARIZONIX_APP_VERSION`                            | Non-empty version returned by health and OpenAPI metadata          | `0.1.0`                  | Server response includes version       | API startup               |
| `ARIZONIX_LOG_LEVEL`                              | `debug`, `info`, `warning`, `error`, or `critical`                 | `info`                   | Server-only                            | API startup               |
| `ARIZONIX_ALLOWED_ORIGINS`                        | Comma-separated or JSON array of exact HTTP(S) browser origins     | Local ports 3000         | Server-only                            | API startup               |
| `ARIZONIX_SUPABASE_URL`                           | Supabase project origin used to derive the JWT issuer and JWKS URL | None; `/me` fails closed | Server-only, not secret                | API startup               |
| `ARIZONIX_SUPABASE_JWT_AUDIENCE`                  | Required access-token audience                                     | `authenticated`          | Server-only, not secret                | API startup               |
| `ARIZONIX_SUPABASE_JWKS_CACHE_SECONDS`            | Successful JWKS cache TTL, 1–86400                                 | `600`                    | Server-only                            | API startup               |
| `ARIZONIX_SUPABASE_JWKS_REFRESH_COOLDOWN_SECONDS` | Unknown-key refresh throttle, 1–3600                               | `30`                     | Server-only                            | API startup               |
| `ARIZONIX_SUPABASE_HTTP_TIMEOUT_SECONDS`          | JWKS timeout, greater than 0 and at most 30                        | `5`                      | Server-only                            | API startup               |
| `ARIZONIX_SUPABASE_JWT_CLOCK_SKEW_SECONDS`        | JWT time-claim tolerance, 0–300                                    | `30`                     | Server-only                            | API startup               |
| `NEXT_PUBLIC_API_BASE_URL`                        | HTTP(S) origin of the API, without `/api/v1` or another path       | `http://127.0.0.1:8000`  | Public, embedded in browser JavaScript | Next.js build/dev startup |
| `NEXT_PUBLIC_SITE_URL`                            | Canonical web origin for confirmation redirects                    | `http://127.0.0.1:3000`  | Public                                 | Next.js build/dev startup |
| `NEXT_PUBLIC_SUPABASE_URL`                        | Supabase project origin                                            | Required for auth        | Public                                 | Next.js build/dev startup |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`            | Supabase publishable key                                           | Required for auth        | Public by design                       | Next.js build/dev startup |
| `API_HOST_PORT`                                   | Host loopback port published by Compose for the API                | `8000`                   | Local Compose setting                  | Compose interpolation     |
| `WEB_HOST_PORT`                                   | Host loopback port published by Compose for the web app            | `3000`                   | Local Compose setting                  | Compose interpolation     |

No listed value is a secret. The publishable key is intentionally public. Never place the Supabase service-role key, a JWT signing key, or any other secret in a `NEXT_PUBLIC_` variable because Next.js embeds it into the browser bundle. This step does not use a service-role key.

## Supabase dashboard setup

1. Create or select a Supabase project. Copy its project URL and publishable key into `apps/web/.env.local`. Put the same project URL, but no key, in `apps/api/.env`.
2. In **Authentication → URL Configuration**, set the local Site URL to `http://127.0.0.1:3000` and allow `http://127.0.0.1:3000/auth/confirm` as a redirect URL. Add the deployed HTTPS origin and callback before deployment.
3. Keep email/password sign-up and email confirmation enabled. Set the dashboard minimum password length to 8 so provider policy matches the UI and server validation.
4. Set the confirmation email link to `{{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email`. The application supplies a trusted `/auth/confirm?next=…` URL and removes the token from the browser address immediately after verification.
5. Use an asymmetric signing key (RS256 or ES256). Projects using the legacy shared HS256 secret must rotate to an asymmetric key; the API intentionally provides no shared-secret fallback.

Restart both applications after changing auth configuration. Missing or malformed web auth configuration displays corrective setup guidance. Missing API auth configuration leaves `/api/v1/health` public but makes `/api/v1/me` return a controlled 503.

Sign-out clears the local browser session. An access JWT already presented elsewhere remains valid until its short expiry unless revoked by additional Supabase controls; this step does not claim instant global JWT revocation.

The public API convention is origin-only. The client owns the `/api/v1/health` path. Rejecting path-bearing base URLs prevents accidental requests such as `/api/v1/api/v1/health`.

## Files and ownership

- `apps/api/.env.example` documents direct API defaults. Copy it to ignored `apps/api/.env` for direct development.
- `apps/web/.env.example` documents the browser-visible Next.js value. Copy it to ignored `apps/web/.env.local` for direct development.
- Root `.env.example` documents Compose interpolation. Copy it to ignored root `.env` only when using Compose.
- `compose.yaml` explicitly passes server settings to the API and passes the public API origin as a web image build argument.

These files serve different launch modes and do not automatically override one another.

## Precedence

For direct API development, Pydantic Settings resolves process environment variables first, then `apps/api/.env`, then code defaults. Tests pass `_env_file=None` and explicitly isolate relevant process variables, so a developer file cannot change test outcomes.

For direct Next.js development and builds, Next.js uses its documented order: process environment, environment-specific local file, `.env.local`, environment-specific file, then `.env`. All `NEXT_PUBLIC_` values are frozen into browser JavaScript when Next.js builds.

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

The frontend accepts only HTTP(S) origins and normalizes one trailing slash through URL origin parsing. Invalid API configuration produces a concise health-card correction and no health request; invalid auth configuration produces a dedicated setup screen and does not expose protected content. Raw exceptions, environment contents, and secrets are not displayed.
