#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Check for .env
if [[ ! -f ".env" ]]; then
  echo "Missing .env in $ROOT_DIR" >&2
  echo "Create .env with: USERNAME, PASSWORD, THERMOMIX_LOCALE (default: de)" >&2
  exit 1
fi

# Create data directory
mkdir -p "$ROOT_DIR/data"

# Build docker image
echo "[start.sh] Building docker image..."
docker build -t thermomix-scraper:local "$ROOT_DIR"

# Parse optional arguments
MODE="${1:-skip}"  # skip, update, redownload, continue

# Run the scraper
echo "[start.sh] Starting recipe scraper (mode: $MODE) -> ./data"
echo ""

docker run --rm \
  --env-file "$ROOT_DIR/.env" \
  -v "$ROOT_DIR/data:/data" \
  thermomix-scraper:local \
  --mode "$MODE"

echo ""
echo "[start.sh] Done! Recipes saved to ./data/"
echo "[start.sh] Total recipes: $(ls -1 "$ROOT_DIR/data"/r*.json 2>/dev/null | wc -l | tr -d ' ')"
