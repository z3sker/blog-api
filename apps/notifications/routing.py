from __future__ import annotations

from django.urls import re_path

from apps.notifications.consumers import CommentConsumer


websocket_urlpatterns = [
    re_path(r"^ws/posts/(?P<slug>[-\w]+)/comments/$", CommentConsumer.as_asgi()),
]

