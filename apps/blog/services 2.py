from __future__ import annotations

import json
import logging
from typing import Any

from django.core.cache import cache
from django_redis import get_redis_connection

from .constants import (
    CACHE_KEY_POSTS_PUBLISHED_VERSION,
    REDIS_COMMENTS_CHANNEL,
)

logger = logging.getLogger("blog")


def bump_published_posts_cache_version() -> None:
    try:
        cache.incr(CACHE_KEY_POSTS_PUBLISHED_VERSION)
    except ValueError:
        cache.set(CACHE_KEY_POSTS_PUBLISHED_VERSION, 1, timeout=None)


def get_published_posts_cache_version() -> int:
    version = cache.get(CACHE_KEY_POSTS_PUBLISHED_VERSION)
    if version is None:
        cache.set(CACHE_KEY_POSTS_PUBLISHED_VERSION, 1, timeout=None)
        return 1
    return int(version)


def publish_comment_event(payload: dict[str, Any]) -> None:
    try:
        redis_client = get_redis_connection("default")
        redis_client.publish(REDIS_COMMENTS_CHANNEL, json.dumps(payload))
    except Exception:
        logger.exception("Failed to publish comment event")
