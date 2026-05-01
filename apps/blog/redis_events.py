from __future__ import annotations

import json
from typing import Any

import redis
from django.conf import settings


COMMENTS_CHANNEL = "comments"
POSTS_CHANNEL = "published_posts"


def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_comment_created(payload: dict[str, Any]) -> int:
    client = get_redis_client()
    return client.publish(COMMENTS_CHANNEL, json.dumps(payload))


def publish_post_published(payload: dict[str, Any]) -> int:
    client = get_redis_client()
    return client.publish(POSTS_CHANNEL, json.dumps(payload))

