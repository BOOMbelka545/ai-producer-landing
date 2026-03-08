## Summary
- What changed?
- Why is this needed?

## Scope
- [ ] landing
- [ ] backend
- [ ] ios

## Quality Gates
- [ ] CI is green
- [ ] No secrets in code/diff
- [ ] Security checks passed
- [ ] Smoke checks passed

## Deploy Impact
- [ ] No deploy impact
- [ ] Deploy required (CD should run from protected `main`/`release/*`)
- [ ] Rollback plan confirmed

## Verification
- [ ] `/` responds 200 in test/smoke
- [ ] Primary CTA exists (`data-cta-id="hero_main"`)
- [ ] Screenshots/logs attached (if UI-impacting)

## Checklist
- [ ] I updated docs/runbook when behavior changed
- [ ] I confirmed environment-specific config (`dev/stage/prod`)
- [ ] I verified no breaking changes for unrelated repos
