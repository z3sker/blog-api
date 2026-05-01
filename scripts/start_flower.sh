#!/usr/bin/env bash
set -Eeuo pipefail

exec celery -A settings flower \
  --address=0.0.0.0 \
  --port=5555 \
  --basic-auth="${BLOG_FLOWER_USER}:${BLOG_FLOWER_PASSWORD}"
