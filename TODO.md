# TODO Tracker

Last update: 2026-03-09

## Epic: product-analytics-mixpanel-coverage
- [x] Branch: `codex/epic-product-analytics-mixpanel-coverage`
- [x] Product analytics framework documented (`docs/analytics/mixpanel-plan.md`).
- [x] Canonical event taxonomy (snake_case, typed events, no duplicates by naming).
- [x] Unified analytics abstraction layer enforced (`AnalyticsService` only).
- [x] Global Mixpanel event properties standardized (`platform/app_version/build_number/environment/session_id/timestamp_client/user_id/anonymous_id`).
- [x] MVP event coverage wired for onboarding/auth, activation, engagement, monetization intent.
- [x] People properties updates wired for lifecycle/profile fields.
- [x] QA checklist documented (`docs/analytics/mixpanel-qa-checklist.md`).
- [ ] Mixpanel dashboards created in workspace (manual product-owner step with workspace access).

## Follow-up / residual risks (product analytics)
- [ ] Connect real billing callbacks for `purchase_succeeded`, `trial_converted`, `trial_canceled`.
- [ ] Add explicit push payload integration for stronger `push_opened` attribution.
- [ ] Configure and share production Mixpanel dashboard URLs.

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

## Epic: ci-cd-landing-phase1
- [ ] Branch: `codex/epic-cicd-landing-phase1`
- [ ] Add CI workflow for landing (lint + build + basic security checks).
- [ ] Add CD workflow for landing deploy from protected `main`.
- [ ] Add post-deploy health check and cache invalidation.
- [ ] Validate rollback flow at least once.
- [ ] Update runbook/docs for landing delivery.

## CI/CD follow-up for other repositories
- [ ] Backend CI/CD phase (lint/tests/migrations + stage/prod deploy gates).
- [ ] iOS CI/CD phase (build/tests + TestFlight automation).
- [ ] Cross-repo release governance (branch protection + required checks).
