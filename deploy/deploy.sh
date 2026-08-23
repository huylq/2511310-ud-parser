#!/usr/bin/env bash
# Deploy the VietNLP stack to server _59.
#
# Sync -> build -> test -> up. Tests run inside the built image before anything
# starts, so a broken build never becomes a running service.
#
# Usage:  ./deploy/deploy.sh [--host _59] [--path ~/vietnlp] [--with-graph]

set -euo pipefail

HOST="_59"
REMOTE_PATH="vietnlp"
PROFILES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --path) REMOTE_PATH="$2"; shift 2 ;;
    --with-graph) PROFILES+=(--profile graph); shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> syncing source to ${HOST}:${REMOTE_PATH}"
ssh "$HOST" "mkdir -p ${REMOTE_PATH}"
# tar over ssh rather than rsync: the target host has no rsync, and requiring one
# more package on a shared box we do not administer is not worth it.
# Secrets are never synced -- deploy/.env exists only on the server.
tar czf - \
  --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.env' --exclude 'deepseek.key' --exclude 'data' \
  --exclude '.venv' --exclude '*.egg-info' --exclude '.pytest_cache' \
  src pyproject.toml tests deploy CLAUDE.md \
  | ssh "$HOST" "tar xzf - -C ${REMOTE_PATH}"

echo "==> checking for deploy/.env on the server"
if ! ssh "$HOST" "test -f ${REMOTE_PATH}/deploy/.env"; then
  echo "ERROR: ${REMOTE_PATH}/deploy/.env is missing on ${HOST}." >&2
  echo "Copy deploy/.env.example there and fill in the secrets, then re-run." >&2
  exit 1
fi

echo "==> building image"
ssh "$HOST" "cd ${REMOTE_PATH}/deploy && docker compose build agents"

echo "==> running the test suite inside the image"
ssh "$HOST" "cd ${REMOTE_PATH}/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q"

echo "==> starting services"
ssh "$HOST" "cd ${REMOTE_PATH}/deploy && docker compose ${PROFILES[*]:-} up -d --remove-orphans"

echo "==> status"
ssh "$HOST" "cd ${REMOTE_PATH}/deploy && docker compose ps"

cat <<'TUNNEL'

Services bind to 127.0.0.1 on the server. Reach them with a tunnel:

  ssh -N -L 6042:127.0.0.1:6042 -L 6043:127.0.0.1:6043 -L 6044:127.0.0.1:6044 _59

  postgres  localhost:6042
  minio     localhost:6043   console localhost:6044
TUNNEL
