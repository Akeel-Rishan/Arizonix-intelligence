# Authentication

## Boundary and flow

Step 2.1 establishes identity, not complete authorization:

```text
Browser ── email/password + cookie session ──> Supabase Auth
   │                                              │
   │ Next.js SSR proxy refreshes cookies          │ signed access JWT
   │ protected layout verifies claims             │
   └── Authorization: Bearer <access JWT> ──> FastAPI /api/v1/me
                                                   │
                                                   └── trusted Supabase JWKS
```

The six application routes are server-protected. The Next.js 16 proxy refreshes the official Supabase SSR cookie session, and the protected layout calls verified `getClaims()` before rendering. Proxy routing is not the only enforcement point: every future server action and API operation that reads private business data must still perform authorization.

The browser obtains its current access token from the Supabase session only when calling the configured Arizonix API origin. It never stores a second token in local storage. A 401 permits one coordinated session refresh and one retry; a 503 is shown as a verification-service outage. Tokens and confirmation parameters are not logged or rendered.

FastAPI derives the issuer and `/.well-known/jwks.json` endpoint from `ARIZONIX_SUPABASE_URL`. It permits only RS256 and ES256, verifies the signature and standard identity/time claims, caches keys for a bounded interval, throttles attacker-controlled unknown-key refreshes, and fails closed when no trusted key is available. Legacy HS256 projects must migrate to an asymmetric signing key.

## Project and environment setup

Copy the examples if the ignored local files do not exist:

```powershell
Copy-Item apps/web/.env.example apps/web/.env.local
Copy-Item apps/api/.env.example apps/api/.env
```

Set these browser-visible values in `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_REPLACE_ME
```

Set the matching project origin in `apps/api/.env`:

```dotenv
ARIZONIX_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
ARIZONIX_SUPABASE_JWT_AUDIENCE=authenticated
```

The publishable key is intentionally public. Do not use or expose a service-role key, JWT signing secret, private key, or another credential. Restart both applications after changing these values; public Next.js variables are embedded at build/dev startup.

In the Supabase dashboard:

1. Select an asymmetric RS256 or ES256 signing key under project signing-key settings. Rotate away from the legacy shared JWT secret if necessary.
2. Enable email/password sign-up and email confirmation.
3. Set the minimum password length to 8. The UI and server enforce the same minimum without inventing additional complexity rules.
4. Under **Authentication → URL Configuration**, set the local Site URL to `http://127.0.0.1:3000`.
5. Add exactly `http://127.0.0.1:3000/auth/confirm` to the local redirect allowlist. Add only the exact deployed HTTPS callback when deploying; do not use a broad production wildcard.
6. Set the confirmation email link to:

   ```text
   {{ .RedirectTo }}&token_hash={{ .TokenHash }}&type=email
   ```

The sign-up action supplies `.RedirectTo` as the trusted callback with a validated internal `next` value. The callback accepts only the email OTP type, verifies the token server-side, establishes the cookie session, and immediately redirects to a token-free URL. Invalid, expired, and reused links return to sign-in with generic guidance.

## Cookies, refresh, CSRF, and sign-out

`@supabase/ssr` owns the single cookie-backed session. Cookies use path `/`, `SameSite=Lax`, and `Secure` when `NEXT_PUBLIC_SITE_URL` is HTTPS. The browser SDK must be able to manage session material, so these are not treated as an HttpOnly server-only session. This makes strict XSS prevention, HTTPS deployment, and avoiding untrusted scripts important.

Cookie-writing Server Actions rely on Next.js' same-origin `Origin`/`Host` validation in addition to `SameSite=Lax`. Sign-out is a POST Server Action and uses Supabase's `local` scope: it clears this browser's session and returns to login. It does not promise immediate global revocation. An access JWT already copied elsewhere can remain valid until expiry unless later revocation controls are introduced.

Authenticated HTML is dynamically rendered, refreshed auth responses carry no-cache headers from the SSR adapter, and `/api/v1/me` sends `Cache-Control: no-store`.

## Direct and Docker startup

For direct development, start the processes in separate terminals:

```powershell
Set-Location apps/api
uv run uvicorn arizonix_api.main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
Set-Location apps/web
npm run dev
```

For Compose, copy the root example, replace the Supabase placeholders, and rebuild because public values are build arguments:

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
```

If auth configuration is missing or malformed, protected frontend content fails closed and displays setup guidance. `/api/v1/health` remains public; authenticated `/api/v1/me` returns 503 when backend verification is not configured.

## Manual live verification

Use only your own test account:

1. Configure the real project and restart both applications.
2. Visit `/signup`, register the test account, and verify the check-email screen appears without claiming a session.
3. Open the confirmation email. Confirm the final URL contains no `token_hash` and reaches Overview or the safe original destination.
4. Sign in and open Overview, Prospects, Research, Evidence, Human Review, and Settings.
5. On Settings, confirm `/api/v1/me` shows only the expected user ID and optional email.
6. Reload and confirm the session persists. Allow normal SDK refresh behavior to occur; do not edit cookies or fabricate tokens.
7. Sign out, then directly request a protected URL and confirm it returns to login.
8. Call `/api/v1/me` without a bearer token and confirm 401 plus `WWW-Authenticate: Bearer`.
9. Call `/api/v1/health` without authentication and confirm 200.

The repository's deterministic suite exercises the same SDK and cookie flow against a test-only protocol-compatible server. Actual confirmation delivery, a real Supabase session refresh, and end-to-end sign-in against the user's project are **NOT RUN** until the user performs this checklist.

## Troubleshooting

- **Setup screen:** verify both public web values and `ARIZONIX_SUPABASE_URL`, then restart or rebuild.
- **Confirmation returns to login:** check the exact Site URL, callback allowlist, template, token age, and `127.0.0.1` versus `localhost` host consistency.
- **Session disappears:** ensure proxy cookie headers are not stripped by a reverse proxy and the deployed `NEXT_PUBLIC_SITE_URL` uses HTTPS.
- **CORS failure on `/me`:** add the exact frontend origin to `ARIZONIX_ALLOWED_ORIGINS`; do not use `*`. `Authorization` is already allowed by the API.
- **503 from `/me`:** verify the API can reach the configured trusted JWKS endpoint and that the project uses an asymmetric signing key.
- **401 from `/me`:** sign in again and confirm issuer, audience, subject, expiry, and project URL match. Public errors intentionally omit cryptographic detail.

Workspace membership, roles, database migrations, and row-level security are implemented in Step 2.2.
A valid identity alone grants no workspace access; see [authorization.md](authorization.md). Step 2.3
adds transaction-local request correlation, durable successful-mutation events, and redacted security
logs; see [audit-logging.md](audit-logging.md). Step 3.1 company authorization uses the same verified
identity and transaction context; see [company-management.md](company-management.md). Invitations and
later evidence/research authorization remain deferred.
