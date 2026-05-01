from __future__ import annotations

import json
import logging

import redis.asyncio as redis
from django.conf import settings
from django.http import HttpRequest, StreamingHttpResponse

from apps.blog.redis_events import POSTS_CHANNEL


logger = logging.getLogger("blog")
SSE_RETRY_MILLISECONDS = 5000


async def post_publication_stream(request: HttpRequest) -> StreamingHttpResponse:
    # SSE is ideal for one-way publication updates; use WebSockets when the browser must also send real-time messages back.
    async def event_stream():
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = client.pubsub()
        try:
            await pubsub.subscribe(POSTS_CHANNEL)
            yield f"retry: {SSE_RETRY_MILLISECONDS}\n\n"
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                yield f"data: {message['data']}\n\n"
        except Exception as exc:
            logger.exception("SSE stream failed.")
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        finally:
            await pubsub.close()
            await client.aclose()

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
