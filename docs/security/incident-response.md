# Incident Response: Analytics Access Security

Last updated: 2026-03-07

## Signals to monitor
- Spike in `401/403` for `/analytics` and `/api/v1/analytics/*`.
- Repeated denied attempts from same IP.
- Unexpected allowed requests outside owner IP range (if allowlist enabled).

## Immediate actions
1. Rotate analytics credentials:
   - Change `ANALYTICS_BASIC_PASSWORD_HASH` (or password + restart).
2. Rotate session secret:
   - Change `ANALYTICS_SESSION_SECRET` and restart service.
3. If needed, enable strict allowlist:
   - `ANALYTICS_IP_ALLOWLIST_ENABLED=true`
   - set `ANALYTICS_IP_ALLOWLIST`.
4. Clear active process and restart:
   - `systemctl restart landing`

## Forensics
- Review access log file: `landing/data/analytics-access.jsonl`.
- Confirm denied reasons: `auth_failed`, `not_owner`, `ip_blocked`, `lockout`.
- Cross-check with reverse-proxy logs.
