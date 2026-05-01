from __future__ import annotations

import asyncio

import httpx
from asgiref.sync import sync_to_async
from django.http import JsonResponse

from apps.blog.models import Comment, Post
from apps.users.models import User


EXCHANGE_URL = "https://open.er-api.com/v6/latest/USD"
TIME_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty"
EXCHANGE_RATE_CODES = ("KZT", "RUB", "EUR")
HTTP_TIMEOUT_SECONDS = 10


async def fetch_exchange_rates(client: httpx.AsyncClient) -> dict[str, float]:
    response = await client.get(EXCHANGE_URL)
    response.raise_for_status()
    rates = response.json().get("rates", {})
    return {code: rates[code] for code in EXCHANGE_RATE_CODES if code in rates}


async def fetch_current_time(client: httpx.AsyncClient) -> str:
    response = await client.get(TIME_URL)
    response.raise_for_status()
    return response.json()["dateTime"]


async def stats_view(request: object) -> JsonResponse:
    # Async keeps the two public HTTP requests in flight together; sync code would wait for one API before starting the next.
    total_posts, total_comments, total_users = await asyncio.gather(
        sync_to_async(Post.objects.count)(),
        sync_to_async(Comment.objects.count)(),
        sync_to_async(User.objects.count)(),
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        exchange_rates, current_time = await asyncio.gather(
            fetch_exchange_rates(client),
            fetch_current_time(client),
        )

    return JsonResponse(
        {
            "blog": {
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_users": total_users,
            },
            "exchange_rates": exchange_rates,
            "current_time": current_time,
        }
    )
