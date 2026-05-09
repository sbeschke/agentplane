#!/usr/bin/env bash
# Run PostgreSQL with pgvector for local development (started by process-compose).
set -euo pipefail

PORT="${AGENTPLANE_PG_PORT:-55432}"
NAME="${AGENTPLANE_PG_CONTAINER:-agentplane-postgres-dev}"
IMAGE="${AGENTPLANE_PG_IMAGE:-pgvector/pgvector:pg17}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the dev Postgres service. Install Docker and try again." >&2
  exit 1
fi

docker rm -f "${NAME}" >/dev/null 2>&1 || true

exec docker run --rm \
  --name "${NAME}" \
  -p "${PORT}:5432" \
  -e POSTGRES_USER=agentplane \
  -e POSTGRES_PASSWORD=agentplane \
  -e POSTGRES_DB=agentplane \
  -v agentplane_pgdata:/var/lib/postgresql/data \
  "${IMAGE}"
