# Landing CI/CD Runbook (Phase 1)

## Scope
- Repo root: `/Users/leo/Desktop/Production`
- Project: `landing`
- CI workflow: `.github/workflows/landing-ci.yml`
- CD workflow: `.github/workflows/landing-cd.yml`
- Rollback workflow: `.github/workflows/landing-rollback.yml`

## Required GitHub Branch Rules
Enable on `main` (and each protected `release/*` branch):
1. Require pull request before merging.
2. Require status checks to pass before merging.
3. Add required check: `quality-security-build` from `landing-ci`.
4. Restrict direct pushes to protected branches.

## CI Quality Gates
On every PR/push affecting `landing/**`:
1. HTML validation (`htmlhint`).
2. CSS lint (`stylelint`).
3. JS lint (`eslint`).
4. Static artifact build (`landing/dist/landing-site-<sha>.tar.gz`).
5. Dependency audit (`npm audit --audit-level=high`).
6. Secret scan (`gitleaks`).
7. Smoke check:
- local server returns `/` with HTTP 200
- HTML contains primary CTA marker: `data-cta-id="hero_main"`

## CD Flow
Trigger: push to protected `main` or `release/*` with changes under `landing/**`.
1. Build static artifact.
2. Upload artifact to host over SSH.
3. Create release directory `${LANDING_DEPLOY_PATH}/releases/<release-id>`.
4. Switch `${LANDING_DEPLOY_PATH}/current` symlink to new release.
5. Invalidate CDN via `LANDING_CDN_INVALIDATION_URL`.
6. Run post-deploy check against `LANDING_SITE_URL`:
- `/` returns 200
- response body is non-empty
- contains `data-cta-id="hero_main"`
7. Send deploy status to `LANDING_NOTIFY_WEBHOOK_URL`.

## Rollback
Manual trigger: `landing-rollback` workflow.
1. Optional input `release_id`.
2. If empty, workflow picks previous release (`2nd newest`).
3. `current` symlink is switched to target release.
4. Health-check runs automatically.
5. Notification sent to webhook.

## Secrets (GitHub Actions)
Store only in repository/environment secrets:
- `LANDING_DEPLOY_HOST`
- `LANDING_DEPLOY_USER`
- `LANDING_DEPLOY_PORT`
- `LANDING_DEPLOY_PATH`
- `LANDING_DEPLOY_SSH_KEY`
- `LANDING_SITE_URL`
- `LANDING_CDN_INVALIDATION_URL`
- `LANDING_CDN_INVALIDATION_TOKEN` (optional if endpoint allows anonymous purge)
- `LANDING_NOTIFY_WEBHOOK_URL` (Slack/Teams/custom webhook)

## Incident Response
1. If deploy fails: review `landing-cd` logs, fix root cause, re-run after patch.
2. If post-deploy check fails on production: run `landing-rollback` immediately.
3. Validate rollback health-check.
4. Create incident note with:
- failed release id
- rollback target id
- root cause
- preventive action

## DoD Evidence (Phase 1)
To close phase 1, attach in epic:
1. Screenshot/log of blocked merge on red `landing-ci`.
2. Screenshot/log of successful auto-deploy from `main`.
3. Screenshot/log of post-deploy health-check success.
4. Screenshot/log of at least one tested rollback run.
