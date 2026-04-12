from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment, Post

logger = logging.getLogger("blog")

EXCHANGE_RATES_URL = "https://open.er-api.com/v6/latest/USD"
TIME_API_URL = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty"
EXCHANGE_KEYS = ("KZT", "RUB", "EUR")


class StatsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Stats"],
        summary="Get combined statistics",
        description=(
            "Returns blog statistics combined with exchange rates and current time for Almaty. "
            "External calls are performed concurrently using asyncio.gather."
        ),
        responses={
            200: OpenApiResponse(description="Stats response"),
            502: OpenApiResponse(description="External services unavailable"),
        },
        examples=[
            OpenApiExample(
                "Response",
                value={
                    "blog": {"total_posts": 42, "total_comments": 137, "total_users": 15},
                    "exchange_rates": {"KZT": 450.23, "RUB": 89.1, "EUR": 0.92},
                    "current_time": "2024-03-15T18:30:00+05:00",
                },
                response_only=True,
            )
        ],
    )
    async def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Async is used here because two independent external HTTP requests can be awaited concurrently.
        # A synchronous implementation would block on the first request before starting the second.
        blog_counts = await sync_to_async(self._get_blog_counts)()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                rates_task = self._fetch_exchange_rates(client)
                time_task = self._fetch_current_time(client)
                exchange_rates, current_time = await asyncio.gather(rates_task, time_task)
        except Exception:
            logger.exception("Stats external fetch failed")
            return Response({"detail": _("External services unavailable.")}, status=502)

        return Response(
            {
                "blog": blog_counts,
                "exchange_rates": exchange_rates,
                "current_time": current_time,
            }
        )

    @staticmethod
    def _get_blog_counts() -> dict[str, int]:
        User = get_user_model()
        return {
            "total_posts": Post.objects.count(),
            "total_comments": Comment.objects.count(),
            "total_users": User.objects.count(),
        }

    async def _fetch_exchange_rates(self, client: httpx.AsyncClient) -> dict[str, float]:
        response = await client.get(EXCHANGE_RATES_URL)
        response.raise_for_status()
        data = response.json()
        rates = data.get("rates", {})
        return {key: float(rates[key]) for key in EXCHANGE_KEYS if key in rates}

    async def _fetch_current_time(self, client: httpx.AsyncClient) -> str:
        response = await client.get(TIME_API_URL)
        response.raise_for_status()
        data = response.json()
        date_time = data.get("dateTime")
        if isinstance(date_time, str) and date_time:
            try:
                parsed = datetime.fromisoformat(date_time)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.get_fixed_timezone(300))
                return parsed.isoformat()
            except Exception:
                return date_time
        return timezone.now().isoformat()
