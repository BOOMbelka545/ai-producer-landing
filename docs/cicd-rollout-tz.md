# CI/CD Technical Spec (Phased by Repositories)

Last update: 2026-03-07  
Owner: Leo + Engineering

## Goal
Build CI/CD incrementally across separate repositories:
1. First: landing deployment pipeline.
2. Then: backend.
3. Then: iOS app pipeline.

This split is mandatory because repos have different tech stacks, release models, and risk profiles.

## Phase 1 (Priority): Landing CI/CD

### Scope
- Repo: `/Users/leo/Desktop/Production` (landing folder).
- Branch: `codex/epic-cicd-landing-phase1`.
- Trigger:
  - CI on every PR and push.
  - CD only from `main` (or explicit release branch).

### CI requirements
1. Install dependencies and run static checks:
   - HTML validation
   - CSS lint
   - JS lint
2. Build artifact (static package).
3. Security checks:
   - basic dependency audit (if package manager present)
   - secret scan in repository
4. Smoke check:
   - verify landing starts and key route returns 200
   - optional basic Lighthouse budget check (performance floor)

### CD requirements
1. Deploy static build to target hosting.
2. Invalidate CDN/cache after successful deploy.
3. Health check after deploy:
   - `/` returns 200
   - page contains primary CTA marker
4. Rollback:
   - support redeploy of previous artifact/tag.
5. Notifications:
   - deployment status (success/fail) to owner channel.

### Security requirements
- Deploy credentials only via CI secrets.
- No credentials in git.
- Production deploy requires protected branch + required checks.

### Definition of Done (Phase 1)
- PR cannot merge without green CI.
- Merge to `main` triggers automated deploy.
- Post-deploy health check runs automatically.
- Rollback is documented and tested at least once.

## Phase 2: Backend CI/CD

### CI
- `ruff`, `pytest`, migration check.
- OpenAPI drift check.
- Security scan for dependencies.

### CD
- Deploy to staging first, then production promotion.
- Run DB migrations safely.
- Readiness check endpoint required.
- Rollback procedure with previous image/version.

## Phase 3: iOS CI/CD

### CI
- Build in CI for target scheme.
- Unit tests.
- Optional screenshot/UI smoke tests.

### CD
- Automated TestFlight upload for release branch/tag.
- Build number/version automation.
- Release notes generation.

## Cross-project governance
1. Protected branches (`main`) + required status checks.
2. Conventional commit policy and PR template.
3. Environment separation: dev/stage/prod.
4. Incident response runbook linked in each repo.

## Non-goals
- Full enterprise release orchestration in one step.
- Multi-region deploy and advanced canary (can be follow-up).
