#!/usr/bin/env bash
set -euo pipefail

SERVE_DIR="${1:-./dist/site}"
PORT="${SMOKE_PORT:-18081}"
TARGET_URL="http://127.0.0.1:${PORT}/"
CTA_MARKER='data-cta-id="hero_main"'

if [ ! -f "$SERVE_DIR/index.html" ]; then
  echo "Smoke failed: missing $SERVE_DIR/index.html"
  exit 1
fi

python3 -m http.server "$PORT" --directory "$SERVE_DIR" >/tmp/landing-smoke-server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

for _ in {1..20}; do
  if curl -fsS -o /tmp/landing-smoke-body.html -w "%{http_code}" "$TARGET_URL" | grep -q "^200$"; then
    break
  fi
  sleep 0.3
done

STATUS_CODE="$(curl -sS -o /tmp/landing-smoke-body.html -w "%{http_code}" "$TARGET_URL")"
if [ "$STATUS_CODE" != "200" ]; then
  echo "Smoke failed: / returned HTTP $STATUS_CODE"
  exit 1
fi

if ! grep -q "$CTA_MARKER" /tmp/landing-smoke-body.html; then
  echo "Smoke failed: primary CTA marker not found"
  exit 1
fi

echo "Smoke passed: / is 200 and CTA marker found"
