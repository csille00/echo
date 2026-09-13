#!/usr/bin/env bash
# Pull latest main and rebuild the API container on the Supabase host.
set -euo pipefail

REPO_DIR="${JOURNAL_SEARCH_DIR:-$HOME/journal-search}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.supabase.yml}"
API_PORT="${API_PORT:-8000}"

cd "$REPO_DIR"

git fetch origin main
git checkout main
git pull --ff-only origin main

docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

echo "Waiting for API health on :${API_PORT}..."
for _ in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT}/health" >/dev/null; then
    echo "Deploy OK — health check passed"
    exit 0
  fi
  sleep 2
done

echo "Health check failed after 60s"
docker compose -f "$COMPOSE_FILE" logs --tail=50 api
exit 1
