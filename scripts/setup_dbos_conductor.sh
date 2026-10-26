#!/usr/bin/env bash
# Bootstrap self-hosted DBOS Conductor on this machine.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/docker-compose.dbos.yml" ]]; then
  ROOT="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/../docker-compose.dbos.yml" ]]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  echo "docker-compose.dbos.yml not found next to this script or in the parent directory." >&2
  exit 1
fi
cd "$ROOT"

if [[ ! -f .env.dbos ]]; then
  cp .env.dbos.example .env.dbos
  echo "Created .env.dbos — set DBOS_CONDUCTOR_LICENSE_KEY (from https://console.dbos.dev)"
  exit 1
fi

# shellcheck disable=SC1091
source .env.dbos

if [[ -z "${DBOS_CONDUCTOR_LICENSE_KEY:-}" || "${DBOS_CONDUCTOR_LICENSE_KEY}" == "your-trial-license-key-here" ]]; then
  echo "Set DBOS_CONDUCTOR_LICENSE_KEY in .env.dbos first."
  exit 1
fi

docker compose --env-file .env.dbos -f docker-compose.dbos.yml up -d

echo ""
echo "Waiting for Conductor..."
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8090/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

CONSOLE_PORT="${DBOS_CONSOLE_PORT:-18080}"
echo ""
echo "DBOS Conductor is up."
echo "  Console:  http://127.0.0.1:${CONSOLE_PORT}"
echo "  Conductor: ws://127.0.0.1:8090/"
echo ""
echo "Next steps:"
echo "  1. Open the Console (SSH tunnel if remote):"
echo "       ssh -L 18080:localhost:18080 user@your-server"
echo "  2. Register application name: echo"
echo "  3. Generate an API key → set DBOS_CONDUCTOR_KEY in .env"
echo "  4. Start echo API with DBOS_CONDUCTOR_URL=ws://dbos-conductor:8090/"
