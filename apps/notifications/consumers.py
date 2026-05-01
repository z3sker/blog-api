from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.blog.models import Post
from apps.notifications.groups import post_comments_group_name
from apps.users.models import User


UNAUTHORIZED_CLOSE_CODE = 4001
POST_NOT_FOUND_CLOSE_CODE = 4004


class CommentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name = post_comments_group_name(self.slug)

        user = await self.authenticate_user()
        if user is None:
            await self.close(code=UNAUTHORIZED_CLOSE_CODE)
            return

        post_exists = await self.post_exists(self.slug)
        if not post_exists:
            await self.close(code=POST_NOT_FOUND_CLOSE_CODE)
            return

        self.scope["user"] = user
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def comment_message(self, event: dict[str, object]) -> None:
        await self.send_json(event["message"])

    async def authenticate_user(self) -> User | None:
        query_string = self.scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        if not token:
            return None
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
        except (KeyError, TokenError):
            return None
        return await self.get_user(user_id)

    @database_sync_to_async
    def get_user(self, user_id: int) -> User | None:
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def post_exists(self, slug: str) -> bool:
        return Post.objects.filter(slug=slug).exists()
