# Security Baseline: Public Landing + Private Analytics

Last updated: 2026-03-07

## Scope
- Public: `/`, `/index.html`, `/assets/*`, `/api/waitlist`, `/api/analytics-debug` (ingest only).
- Private: `/analytics`, `/api/v1/analytics/*`.

## Controls
- `Basic Auth` on `/analytics` (owner credentials from env only).
- Server-side owner-session guard on `/api/v1/analytics/*`.
- Optional IP allowlist for analytics routes.
- In-memory brute-force protection (attempt window + lockout).
- Security headers:
  - `Strict-Transport-Security`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy`
  - `Content-Security-Policy` (analytics page)
- Directory listing disabled.
- Legacy analytics debug UI/API blocked from public direct access.

## Secrets / Env
- `ANALYTICS_BASIC_USER`
- `ANALYTICS_BASIC_PASSWORD_HASH` (sha256 hex or `sha256$...`)
- `ANALYTICS_BASIC_PASSWORD` (fallback if hash not set)
- `OWNER_USER_ID` / `OWNER_EMAIL`
- `ANALYTICS_SESSION_SECRET`
- `ANALYTICS_IP_ALLOWLIST_ENABLED`
- `ANALYTICS_IP_ALLOWLIST`
- `ANALYTICS_AUTH_MAX_ATTEMPTS`
- `ANALYTICS_AUTH_WINDOW_SEC`
- `ANALYTICS_AUTH_LOCKOUT_SEC`

## Residual Risks
- Brute-force/lockout state is in-memory (resets after process restart).
- Mixpanel relay is async best-effort (no persistent queue yet).
