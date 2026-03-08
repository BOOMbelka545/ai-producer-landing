# TODO Tracker

Last update: 2026-03-07

## Epic: security-private-analytics-for-public-landing
- [x] Branch: `codex/epic-security-private-analytics-for-public-landing`
- [x] Public landing remains open (`/`, assets, waitlist).
- [x] Private analytics page gate: Basic Auth on `/analytics`.
- [x] Owner-only backend guard: `/api/v1/analytics/*`.
- [x] Optional IP allowlist gate implemented.
- [x] Brute-force/lockout controls implemented.
- [x] Security headers baseline enabled.
- [x] Audit log for analytics access attempts implemented.
- [x] Security tests added and passing.
- [x] Security docs updated.

## Follow-up / residual risks
- [ ] Persist brute-force counters in Redis (instead of in-memory).
- [ ] Add durable relay queue + retry worker for Mixpanel forwarding.
- [ ] Add alerting integration for 401/403 spikes.
