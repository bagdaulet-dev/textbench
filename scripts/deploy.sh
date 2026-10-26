#!/usr/bin/env bash
# Run in /opt/textbench on your deployment server.
set -euo pipefail
: "${IMAGE:?Set IMAGE to an immutable GHCR commit tag}"
docker compose -f compose.production.yml config --quiet
docker compose -f compose.production.yml pull
docker compose -f compose.production.yml up -d --wait --wait-timeout 180
docker compose -f compose.production.yml exec -T app python manage.py check --deploy --fail-level WARNING
docker compose -f compose.production.yml exec -T app python manage.py clearsessions
docker compose -f compose.production.yml exec -T app python manage.py purge_expired_analyses
echo "Deployment is healthy."
