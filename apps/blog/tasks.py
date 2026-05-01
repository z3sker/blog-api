from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.blog.models import Comment, Post
from apps.blog.redis_events import publish_post_published
from apps.users.models import User


logger = logging.getLogger("blog")
POST_LIST_CACHE_PREFIX = "posts:list"


def post_published_payload(post: Post) -> dict[str, object]:
    return {
        "post_id": post.id,
        "title": post.title,
        "slug": post.slug,
        "author": {"id": post.author_id, "email": post.author.email},
        "published_at": post.published_at.isoformat(),
    }


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def invalidate_posts_cache() -> None:
    # Retries matter because cache invalidation can fail when Redis restarts; a retry prevents stale post lists from lingering.
    pattern = f"{POST_LIST_CACHE_PREFIX}:*"
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
        return
    cache.clear()


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def publish_scheduled_posts() -> int:
    # Retries matter because scheduled publication updates database state and emits SSE events that should not be silently lost.
    due_posts = Post.objects.select_related("author").filter(status=Post.Status.SCHEDULED, publish_at__lte=timezone.now())
    published_count = 0
    for post in due_posts:
        post.status = Post.Status.PUBLISHED
        post.save(update_fields=["status", "updated_at"])
        publish_post_published(post_published_payload(post))
        published_count += 1
    logger.info("Scheduled posts published: %s", published_count)
    return published_count


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_daily_stats() -> dict[str, int]:
    # Retries matter for daily stats because transient database errors should not permanently skip operational metrics.
    since = timezone.now() - timedelta(days=1)
    stats = {
        "new_posts": Post.objects.filter(created_at__gte=since).count(),
        "new_comments": Comment.objects.filter(created_at__gte=since).count(),
        "new_users": User.objects.filter(date_joined__gte=since).count(),
    }
    logger.info("Daily stats: posts=%s comments=%s users=%s", stats["new_posts"], stats["new_comments"], stats["new_users"])
    return stats

