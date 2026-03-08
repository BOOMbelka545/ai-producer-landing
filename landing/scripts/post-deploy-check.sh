#!/usr/bin/env bash
set -euo pipefail

TARGET_URL="${1:-}"
if [ -z "$TARGET_URL" ]; then
  echo "Usage: post-deploy-check.sh <site-url>"
  exit 1
fi

TMP_BODY="$(mktemp)"
HTTP_CODE="$(curl -sS -L -o "$TMP_BODY" -w "%{http_code}" "$TARGET_URL")"

if [ "$HTTP_CODE" != "200" ]; then
  echo "Health-check failed: $TARGET_URL returned HTTP $HTTP_CODE"
  exit 1
fi

if [ ! -s "$TMP_BODY" ]; then
  echo "Health-check failed: empty response body"
  exit 1
fi

if ! grep -q 'data-cta-id="hero_main"' "$TMP_BODY"; then
  echo "Health-check failed: primary CTA block missing"
  exit 1
fi

echo "Health-check passed for $TARGET_URL"
