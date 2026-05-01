#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT_STEP="startup"
trap 'echo "Entrypoint step failed: ${CURRENT_STEP}" >&2' ERR

CURRENT_STEP="waiting for Redis"
python <<'PY'
import os
import time

import redis

redis_url = os.environ.get("BLOG_REDIS_URL", "redis://redis:6379/0")
client = redis.Redis.from_url(redis_url)
for _ in range(60):
    try:
        client.ping()
        print("Redis is ready.")
        break
    except redis.RedisError:
        time.sleep(1)
else:
    raise SystemExit("Redis did not become available.")
PY

CURRENT_STEP="running migrations"
python manage.py migrate --noinput

CURRENT_STEP="collecting static files"
python manage.py collectstatic --noinput

CURRENT_STEP="compiling translations"
python manage.py compilemessages

if [[ "${BLOG_SEED_DB:-false}" == "true" ]]; then
  CURRENT_STEP="seeding database"
  python manage.py seed
fi

CURRENT_STEP="executing command"
exec "$@"
