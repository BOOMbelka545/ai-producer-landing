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

if [ -d "$ROOT_DIR/data" ]; then
  mkdir -p "$SITE_DIR/data"
  cp "$ROOT_DIR/data/.gitkeep" "$SITE_DIR/data/.gitkeep" 2>/dev/null || true
fi

TAR_NAME="landing-site-${GITHUB_SHA:-local}.tar.gz"
tar -C "$SITE_DIR" -czf "$DIST_DIR/$TAR_NAME" .

echo "Build complete: $DIST_DIR/$TAR_NAME"
