from __future__ import annotations

import logging

import redis
from django.conf import settings
from django.core.management.base import BaseCommand

from ...constants import REDIS_COMMENTS_CHANNEL

logger = logging.getLogger("blog")


class Command(BaseCommand):
    help = "Listen for comment events on Redis channel and print them."

    def handle(self, *args, **options) -> None:
        client = redis.from_url(settings.REDIS_URL)
        pubsub = client.pubsub()
        pubsub.subscribe(REDIS_COMMENTS_CHANNEL)

        logger.info("Subscribed to Redis channel: %s", REDIS_COMMENTS_CHANNEL)
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            self.stdout.write(str(data))
