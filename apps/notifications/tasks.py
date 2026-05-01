from __future__ import annotations

import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.blog.models import Comment
from apps.notifications.groups import post_comments_group_name
from apps.notifications.models import Notification


logger = logging.getLogger("blog")
NOTIFICATION_RETENTION_DAYS = 30


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_new_comment(comment_id: int) -> None:
    # Retries matter here because comment side effects cross the database and channel layer, either of which can fail transiently.
    comment = Comment.objects.select_related("post", "author", "post__author").get(id=comment_id)
    if comment.post.author_id != comment.author_id:
        Notification.objects.get_or_create(recipient=comment.post.author, comment=comment)

    channel_layer = get_channel_layer()
    message = {
        "comment_id": comment.id,
        "author": {"id": comment.author_id, "email": comment.author.email},
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        post_comments_group_name(comment.post.slug),
        {"type": "comment.message", "message": message},
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def clear_expired_notifications() -> int:
    # Retries protect the scheduled cleanup from temporary database failures so old rows are eventually removed.
    cutoff = timezone.now() - timedelta(days=NOTIFICATION_RETENTION_DAYS)
    deleted_count, _details = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Expired notifications deleted: %s", deleted_count)
    return deleted_count
