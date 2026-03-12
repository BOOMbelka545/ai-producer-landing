#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
SITE_DIR="$DIST_DIR/site"

rm -rf "$DIST_DIR"
mkdir -p "$SITE_DIR"

cp "$ROOT_DIR/index.html" "$SITE_DIR/index.html"
cp "$ROOT_DIR/styles.css" "$SITE_DIR/styles.css"
cp "$ROOT_DIR/script.js" "$SITE_DIR/script.js"
cp -R "$ROOT_DIR/assets" "$SITE_DIR/assets"
for extra_page in privacy.html terms.html features.html; do
  if [ -f "$ROOT_DIR/$extra_page" ]; then
    cp "$ROOT_DIR/$extra_page" "$SITE_DIR/$extra_page"
  fi
done
if [ -f "$ROOT_DIR/robots.txt" ]; then
  cp "$ROOT_DIR/robots.txt" "$SITE_DIR/robots.txt"
fi
if [ -f "$ROOT_DIR/sitemap.xml" ]; then
  cp "$ROOT_DIR/sitemap.xml" "$SITE_DIR/sitemap.xml"
fi

if [ -d "$ROOT_DIR/data" ]; then
  mkdir -p "$SITE_DIR/data"
  cp "$ROOT_DIR/data/.gitkeep" "$SITE_DIR/data/.gitkeep" 2>/dev/null || true
fi

# Deploy marker for post-deploy integrity checks (internal + external).
DEPLOY_SHA="${GITHUB_SHA:-local}"
DEPLOY_RELEASE_ID="${RELEASE_ID:-local}"
BUILD_TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat >"$SITE_DIR/deploy-meta.txt" <<EOF
sha=$DEPLOY_SHA
release_id=$DEPLOY_RELEASE_ID
built_at_utc=$BUILD_TS_UTC
EOF

TAR_NAME="landing-site-${GITHUB_SHA:-local}.tar.gz"
tar -C "$SITE_DIR" -czf "$DIST_DIR/$TAR_NAME" .

echo "Build complete: $DIST_DIR/$TAR_NAME"
