from __future__ import annotations

import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from redis.asyncio import Redis

from ...constants import REDIS_COMMENTS_CHANNEL

logger = logging.getLogger("blog")


class Command(BaseCommand):
    help = "Listen for comment events on Redis channel and print them."

    def handle(self, *args, **options) -> None:
        # Async is used here because Redis pub/sub is I/O-bound and can be handled efficiently without blocking.
        # A synchronous listener would block the process while waiting for messages.
        asyncio.run(self._listen())

    async def _listen(self) -> None:
        client: Redis = Redis.from_url(settings.REDIS_URL)
        pubsub = client.pubsub()
        await pubsub.subscribe(REDIS_COMMENTS_CHANNEL)
        logger.info("Subscribed to Redis channel: %s", REDIS_COMMENTS_CHANNEL)

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            self.stdout.write(str(data))
