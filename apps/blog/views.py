from __future__ import annotations

import logging
from typing import Any

from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.utils.decorators import method_decorator

from .constants import (
    CACHE_KEY_POSTS_PUBLISHED_LIST,
    CACHE_TTL_POSTS_LIST_SECONDS,
    RATE_LIMIT_CREATE_POST,
    TOO_MANY_REQUESTS_DETAIL,
)
from .models import Category, Comment, Post, PostStatus, Tag
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    CategorySerializer,
    CommentReadSerializer,
    CommentWriteSerializer,
    PostReadSerializer,
    PostWriteSerializer,
    TagSerializer,
)
from .services import (
    bump_published_posts_cache_version,
    get_published_posts_cache_version,
    publish_comment_event,
)

logger = logging.getLogger("blog")


def too_many_requests() -> Response:
    return Response({"detail": TOO_MANY_REQUESTS_DETAIL}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Post]:
        qs = (
            Post.objects.select_related("author", "category")
            .prefetch_related("tags")
            .all()
        )
        if self.action == "list":
            return qs.filter(status=PostStatus.PUBLISHED)
        if self.request.user and self.request.user.is_authenticated:
            return qs.filter(Q(status=PostStatus.PUBLISHED) | Q(author=self.request.user))
        return qs.filter(status=PostStatus.PUBLISHED)

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return PostReadSerializer
        return PostWriteSerializer

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        if self.action == "comments" and self.request.method == "GET":
            return [AllowAny()]
        if self.action in {"create"} or (self.action == "comments" and self.request.method == "POST"):
            return [IsAuthenticated()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return super().get_permissions()

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Manual caching is used here to keep cache keys stable across pagination and
        # to invalidate the list via a lightweight version bump on create/update/delete.
        page = request.query_params.get("page", "1")
        version = get_published_posts_cache_version()
        cache_key = CACHE_KEY_POSTS_PUBLISHED_LIST.format(version=version, page=page)

        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Posts list cache hit page=%s", page)
            return Response(cached)

        logger.debug("Posts list cache miss page=%s", page)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=CACHE_TTL_POSTS_LIST_SECONDS)
        return response

    @method_decorator(ratelimit(key="user", rate=RATE_LIMIT_CREATE_POST, method="POST", block=False))
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Post create rate limit exceeded for user")
            return too_many_requests()
        logger.info("Post create attempt by user_id=%s", request.user.id)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer: PostWriteSerializer) -> None:
        try:
            post = serializer.save(author=self.request.user)
            bump_published_posts_cache_version()
            logger.info("Post created: %s by user_id=%s", post.slug, self.request.user.id)
        except Exception:
            logger.exception("Post create failed")
            raise

    def perform_update(self, serializer: PostWriteSerializer) -> None:
        try:
            post = serializer.save()
            bump_published_posts_cache_version()
            logger.info("Post updated: %s by user_id=%s", post.slug, self.request.user.id)
        except Exception:
            logger.exception("Post update failed")
            raise

    def perform_destroy(self, instance: Post) -> None:
        slug = instance.slug
        super().perform_destroy(instance)
        bump_published_posts_cache_version()
        logger.info("Post deleted: %s by user_id=%s", slug, self.request.user.id)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = self.get_object()
        if request.method == "GET":
            comments_qs = Comment.objects.select_related("author").filter(post=post)
            serializer = CommentReadSerializer(comments_qs, many=True)
            return Response(serializer.data)

        serializer = CommentWriteSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Comment create failed for post=%s", post.slug)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(
            post=post,
            author=request.user,
            body=serializer.validated_data["body"],
        )
        logger.info("Comment created: id=%s post=%s user_id=%s", comment.id, post.slug, request.user.id)
        publish_comment_event(
            {
                "comment_id": comment.id,
                "post_slug": post.slug,
                "author_email": request.user.email,
                "created_at": comment.created_at.isoformat(),
                "body": comment.body,
            }
        )
        return Response(CommentReadSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Comment.objects.select_related("author", "post").all()

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return CommentReadSerializer
        return CommentWriteSerializer

    def get_permissions(self):
        if self.action in {"retrieve"}:
            return [AllowAny()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return super().get_permissions()

    def perform_update(self, serializer: CommentWriteSerializer) -> None:
        comment = serializer.save()
        logger.info("Comment updated: id=%s user_id=%s", comment.id, self.request.user.id)

    def perform_destroy(self, instance: Comment) -> None:
        comment_id = instance.id
        super().perform_destroy(instance)
        logger.info("Comment deleted: id=%s user_id=%s", comment_id, self.request.user.id)

# Create your views here.
