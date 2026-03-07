# Backend API Notes (Landing)

Last updated: 2026-03-07

## Public
- `POST /api/waitlist`
- `POST /api/analytics-debug` (event ingest + server-side relay enqueue)

## Private (owner-only)
- `GET /api/v1/analytics/events`
- `GET /api/v1/analytics/summary`
- `POST /api/v1/analytics/clear`

## Private page
- `GET /analytics` (Basic Auth required)

## Auth model
- `/analytics`: HTTP Basic Auth (server-side validation).
- `/api/v1/analytics/*`: owner session cookie signed on server.

## Legacy analytics endpoints
- `GET /api/analytics-debug/view` -> blocked (`403`)
- `POST /api/analytics-debug/clear` -> blocked (`403`)
