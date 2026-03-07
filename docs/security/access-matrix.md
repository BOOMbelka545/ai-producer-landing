# Access Matrix

Last updated: 2026-03-07

| Route | Access | Expected |
|---|---|---|
| `/` | Public | `200` |
| `/assets/*` | Public | `200` |
| `/api/waitlist` | Public | `200/400` |
| `/api/analytics-debug` | Public ingest endpoint | `200/400` |
| `/analytics` | Owner only (Basic Auth + allowlist) | `200` else `401/403` |
| `/api/v1/analytics/events` | Owner session only | `200` else `403` |
| `/api/v1/analytics/summary` | Owner session only | `200` else `403` |
| `/api/v1/analytics/clear` | Owner session only | `200` else `403` |
| `/api/analytics-debug/view` | Blocked (legacy private path) | `403` |
| `/api/analytics-debug/clear` | Blocked (legacy private path) | `403` |
