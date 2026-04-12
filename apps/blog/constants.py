from __future__ import annotations

CACHE_TTL_POSTS_LIST_SECONDS = 60
CACHE_KEY_POSTS_PUBLISHED_VERSION = "posts:published:version"
CACHE_KEY_POSTS_PUBLISHED_LIST = "posts:published:list:v{version}:lang:{lang}:tz:{tz}:page:{page}"

RATE_LIMIT_CREATE_POST = "20/m"

REDIS_COMMENTS_CHANNEL = "comments"

TOO_MANY_REQUESTS_DETAIL = "Too many requests. Try again later."
