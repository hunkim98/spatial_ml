#!/usr/bin/env bash
# Start the zone segmentation API server.
#
# Usage:
#   ./api/run.sh            # default: port 8000, auto-reload
#   ./api/run.sh --port 9000
set -euo pipefail
cd "$(dirname "$0")/.."

PORT=8000
for arg in "$@"; do
  case $arg in
    --port=*) PORT="${arg#*=}" ;;
    --port)   shift; PORT="${1:-8000}" ;;
  esac
done

echo "Starting API server on http://localhost:$PORT"
exec uv run uvicorn api.main:app --host 0.0.0.0 --port "$PORT" --reload
