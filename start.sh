#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Check for .env
if [[ ! -f ".env" ]]; then
  echo "Missing .env in $ROOT_DIR" >&2
  echo "Expected: USERNAME=... PASSWORD=... COOKIDOO_LOCALE=de" >&2
  exit 1
fi

# Create data directory
mkdir -p "$ROOT_DIR/data"

# Build docker image (no cache for fresh build)
echo "[start.sh] Building docker image (this may take a minute)..."
docker build --no-cache -t cookidump:local "$ROOT_DIR/cookidump"

# Run the scraper
echo "[start.sh] Starting full recipe dump -> ./data"
echo "[start.sh] This will take several hours for all recipes..."
echo ""

docker run --rm \
  --env-file "$ROOT_DIR/.env" \
  -e COOKIDOO_LOCALE="${COOKIDOO_LOCALE:-de}" \
  -v "$ROOT_DIR/data:/data" \
  cookidump:local \
  --headless \
  --separate-json \
  /usr/bin/chromedriver \
  /data

echo ""
echo "[start.sh] Done! Recipes saved to ./data/"
echo "[start.sh] Total recipes: $(ls -1 "$ROOT_DIR/data"/*.json 2>/dev/null | wc -l | tr -d ' ')"
