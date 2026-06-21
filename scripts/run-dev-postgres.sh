#!/usr/bin/env bash
# Run PostgreSQL with pgvector for local development (started by process-compose).
set -euo pipefail

PORT="${MOPS_PG_PORT:-55432}"
NAME="${MOPS_PG_CONTAINER:-mops-postgres-dev}"
IMAGE="${MOPS_PG_IMAGE:-pgvector/pgvector:pg17}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the dev Postgres service. Install Docker and try again." >&2
  exit 1
fi

docker rm -f "${NAME}" >/dev/null 2>&1 || true

exec docker run --rm \
  --name "${NAME}" \
  -p "${PORT}:5432" \
  -e POSTGRES_USER=mops \
  -e POSTGRES_PASSWORD=mops \
  -e POSTGRES_DB=mops \
  -v mops_pgdata:/var/lib/postgresql/data \
  "${IMAGE}"
