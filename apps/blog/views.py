from __future__ import annotations

import logging
from typing import Any

from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import Q, QuerySet
from django.utils.decorators import method_decorator
from django.utils import timezone, translation

from apps.core.serializers import ErrorDetailSerializer

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


@extend_schema_view(
    list=extend_schema(
        tags=["Posts"],
        summary="List categories",
        description="Returns categories with language-specific names based on active request language.",
        responses={200: CategorySerializer},
        examples=[OpenApiExample("Response", value=[{"id": 1, "name": "Tech", "slug": "tech"}], response_only=True)],
    ),
    retrieve=extend_schema(
        tags=["Posts"],
        summary="Retrieve category",
        description="Returns a single category with language-specific name.",
        responses={200: CategorySerializer, 404: OpenApiResponse(description="Not found")},
        examples=[OpenApiExample("Response", value={"id": 1, "name": "Tech", "slug": "tech"}, response_only=True)],
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        tags=["Posts"],
        summary="List tags",
        description="Returns tags.",
        responses={200: TagSerializer},
        examples=[OpenApiExample("Response", value=[{"id": 1, "name": "Django", "slug": "django"}], response_only=True)],
    ),
    retrieve=extend_schema(
        tags=["Posts"],
        summary="Retrieve tag",
        description="Returns a single tag.",
        responses={200: TagSerializer, 404: OpenApiResponse(description="Not found")},
        examples=[OpenApiExample("Response", value={"id": 1, "name": "Django", "slug": "django"}, response_only=True)],
    ),
)
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class PostViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

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

    @extend_schema(
        tags=["Posts"],
        summary="List published posts",
        description=(
            "Lists published posts with pagination. Response is cached in Redis and cache keys are language/timezone-aware. "
            "Dates include locale-formatted display fields and are converted to the active timezone."
        ),
        responses={200: PostReadSerializer},
        examples=[
            OpenApiExample(
                "Response",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "author": {"id": 1, "email": "user@example.com", "first_name": "John", "last_name": "Doe"},
                            "title": "Hello",
                            "slug": "hello",
                            "body": "Text",
                            "category": {"id": 1, "name": "Tech", "slug": "tech"},
                            "tags": [{"id": 1, "name": "Django", "slug": "django"}],
                            "status": "published",
                            "created_at": "2026-04-12T12:00:00Z",
                            "updated_at": "2026-04-12T12:00:00Z",
                            "created_at_display": "12 апреля 2026 г. 17:00",
                            "updated_at_display": "12 апреля 2026 г. 17:00",
                        }
                    ],
                },
                response_only=True,
            )
        ],
    )
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Manual caching is used here to keep cache keys stable across pagination and
        # to invalidate the list via a lightweight version bump on create/update/delete.
        page = request.query_params.get("page", "1")
        version = get_published_posts_cache_version()
        lang = (translation.get_language() or "en").split("-")[0]
        tz = timezone.get_current_timezone_name()
        cache_key = CACHE_KEY_POSTS_PUBLISHED_LIST.format(version=version, lang=lang, tz=tz, page=page)

        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Posts list cache hit page=%s", page)
            return Response(cached)

        logger.debug("Posts list cache miss page=%s", page)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=CACHE_TTL_POSTS_LIST_SECONDS)
        return response

    @method_decorator(ratelimit(key="user", rate=RATE_LIMIT_CREATE_POST, method="POST", block=False))
    @extend_schema(
        tags=["Posts"],
        summary="Create post",
        description=(
            "Creates a new post for the authenticated user. "
            "Rate-limited per user and invalidates the cached posts list for all languages."
        ),
        request=PostWriteSerializer,
        responses={
            201: PostReadSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized"),
            429: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request",
                value={"title": "Hello", "body": "Text", "status": "draft", "category": None, "tags": []},
                request_only=True,
            ),
        ],
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Post create rate limit exceeded for user")
            return too_many_requests()
        logger.info("Post create attempt by user_id=%s", request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            post = serializer.save(author=request.user)
            bump_published_posts_cache_version()
            logger.info("Post created: %s by user_id=%s", post.slug, request.user.id)
        except Exception:
            logger.exception("Post create failed")
            raise
        headers = self.get_success_headers(serializer.data)
        read_data = PostReadSerializer(post, context=self.get_serializer_context()).data
        return Response(read_data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        tags=["Posts"],
        summary="Retrieve post",
        description="Returns a single post by slug. Anonymous users can access only published posts.",
        responses={200: PostReadSerializer, 404: OpenApiResponse(description="Not found")},
        examples=[OpenApiExample("Response", value={"id": 1, "slug": "hello"}, response_only=True)],
    )
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Update post",
        description="Updates a post by slug. Only the author can edit. Invalidates cached posts list.",
        request=PostWriteSerializer,
        responses={200: PostWriteSerializer, 400: OpenApiResponse(description="Validation error"), 401: OpenApiResponse(description="Unauthorized"), 403: OpenApiResponse(description="Forbidden")},
    )
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Posts"],
        summary="Delete post",
        description="Deletes a post by slug. Only the author can delete. Invalidates cached posts list.",
        responses={204: OpenApiResponse(description="Deleted"), 401: OpenApiResponse(description="Unauthorized"), 403: OpenApiResponse(description="Forbidden"), 404: OpenApiResponse(description="Not found")},
    )
    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().destroy(request, *args, **kwargs)

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
    @extend_schema(
        tags=["Comments"],
        summary="List or create comments",
        description=(
            "GET returns comments for a post (public). POST creates a new comment (auth required) "
            "and publishes a JSON event to Redis channel 'comments'."
        ),
        request=CommentWriteSerializer,
        responses={
            200: CommentReadSerializer,
            201: CommentReadSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        },
        examples=[
            OpenApiExample("Create request", value={"body": "Nice post!"}, request_only=True),
            OpenApiExample(
                "Create response",
                value={"id": 1, "post": 1, "author": {"id": 1, "email": "user@example.com"}, "body": "Nice post!"},
                response_only=True,
            ),
        ],
    )
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
                "author_id": request.user.id,
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
    http_method_names = ["get", "patch", "delete", "head", "options"]

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

    @extend_schema(
        tags=["Comments"],
        summary="Retrieve comment",
        description="Returns a single comment by id.",
        responses={200: CommentReadSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Comments"],
        summary="Update comment",
        description="Updates a comment by id. Only the author can edit.",
        request=CommentWriteSerializer,
        responses={200: CommentWriteSerializer, 400: OpenApiResponse(description="Validation error"), 401: OpenApiResponse(description="Unauthorized"), 403: OpenApiResponse(description="Forbidden")},
        examples=[OpenApiExample("Request", value={"body": "Updated text"}, request_only=True)],
    )
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Comments"],
        summary="Delete comment",
        description="Deletes a comment by id. Only the author can delete.",
        responses={204: OpenApiResponse(description="Deleted"), 401: OpenApiResponse(description="Unauthorized"), 403: OpenApiResponse(description="Forbidden"), 404: OpenApiResponse(description="Not found")},
    )
    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer: CommentWriteSerializer) -> None:
        comment = serializer.save()
        logger.info("Comment updated: id=%s user_id=%s", comment.id, self.request.user.id)

    def perform_destroy(self, instance: Comment) -> None:
        comment_id = instance.id
        super().perform_destroy(instance)
        logger.info("Comment deleted: id=%s user_id=%s", comment_id, self.request.user.id)
