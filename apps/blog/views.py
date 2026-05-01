from __future__ import annotations

import logging

from django.core.cache import cache
from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from apps.blog.tasks import invalidate_posts_cache, post_published_payload
from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.permissions import IsOwnerOrReadOnly
from apps.blog.redis_events import publish_post_published
from apps.blog.serializers import CategorySerializer, CommentSerializer, PostSerializer, TagSerializer
from apps.core.tasks import dispatch_task
from apps.notifications.tasks import process_new_comment
from apps.users.views import rate_limited_response


logger = logging.getLogger("blog")

POST_LIST_CACHE_TIMEOUT = 60
POST_LIST_CACHE_PREFIX = "posts:list"
POST_CREATE_RATE = "20/m"

BLOG_ERROR_RESPONSES = {
    400: OpenApiResponse(description="Validation error."),
    401: OpenApiResponse(description="Authentication credentials were invalid or missing."),
    403: OpenApiResponse(description="Only owners may change this resource."),
    404: OpenApiResponse(description="Resource not found."),
    429: OpenApiResponse(description="Too many requests. Try again later."),
}


def invalidate_post_list_cache() -> None:
    dispatch_task(invalidate_posts_cache)


def publish_post_if_needed(post: Post, previous_status: str | None = None) -> None:
    if post.status != Post.Status.PUBLISHED:
        return
    if previous_status == Post.Status.PUBLISHED:
        return
    try:
        publish_post_published(post_published_payload(post))
    except Exception:
        logger.exception("Published post SSE event failed for post slug: %s", post.slug)


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description="Lists categories with the `name` field translated to the active request language. Authentication is not required.",
        tags=["Posts"],
        responses={200: CategorySerializer, **BLOG_ERROR_RESPONSES},
        examples=[OpenApiExample("Category response", value={"id": 1, "name": "Technology", "slug": "technology"}, response_only=True)],
    ),
    retrieve=extend_schema(
        summary="Get category",
        description="Returns one category by slug with localized name fields. Authentication is not required.",
        tags=["Posts"],
        responses={200: CategorySerializer, **BLOG_ERROR_RESPONSES},
    ),
)
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"


@extend_schema_view(
    list=extend_schema(
        summary="List tags",
        description="Lists all tags. Authentication is not required and no cache is written.",
        tags=["Posts"],
        responses={200: TagSerializer, **BLOG_ERROR_RESPONSES},
        examples=[OpenApiExample("Tag response", value={"id": 1, "name": "django", "slug": "django"}, response_only=True)],
    ),
    retrieve=extend_schema(
        summary="Get tag",
        description="Returns one tag by slug. Authentication is not required.",
        tags=["Posts"],
        responses={200: TagSerializer, **BLOG_ERROR_RESPONSES},
    ),
)
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = "slug"


@extend_schema_view(
    list=extend_schema(
        summary="List posts",
        description=(
            "Lists published posts for anonymous users and also the authenticated user's own drafts. "
            "Responses are paginated, localized, timezone-converted, and cached for 60 seconds with a language-aware cache key."
        ),
        tags=["Posts"],
        responses={200: PostSerializer, **BLOG_ERROR_RESPONSES},
        examples=[OpenApiExample("Posts response", value={"count": 1, "results": [{"title": "First Post", "slug": "first-post"}]}, response_only=True)],
    ),
    retrieve=extend_schema(
        summary="Get post",
        description="Returns one published post by slug. Date fields include localized timezone-converted display values.",
        tags=["Posts"],
        responses={200: PostSerializer, **BLOG_ERROR_RESPONSES},
    ),
    create=extend_schema(
        summary="Create post",
        description=(
            "Creates a post owned by the authenticated user. Authentication is required. "
            "The posts list cache is invalidated for all languages and an SSE event is emitted if the post is published. "
            "Rate limit: 20 requests per minute per user."
        ),
        tags=["Posts"],
        request=PostSerializer,
        responses={201: PostSerializer, **BLOG_ERROR_RESPONSES},
        examples=[
            OpenApiExample(
                "Post create request",
                value={"title": "First Post", "slug": "first-post", "body": "Body", "status": "published", "tags": []},
                request_only=True,
            )
        ],
    ),
    partial_update=extend_schema(
        summary="Update own post",
        description="Partially updates a post. Authentication is required and only the author can update it. Cache is invalidated.",
        tags=["Posts"],
        request=PostSerializer,
        responses={200: PostSerializer, **BLOG_ERROR_RESPONSES},
    ),
    update=extend_schema(
        summary="Replace own post",
        description="Replaces a post. Authentication is required and only the author can replace it. Cache is invalidated.",
        tags=["Posts"],
        request=PostSerializer,
        responses={200: PostSerializer, **BLOG_ERROR_RESPONSES},
    ),
    destroy=extend_schema(
        summary="Delete own post",
        description="Deletes a post. Authentication is required and only the author can delete it. Cache is invalidated.",
        tags=["Posts"],
        responses={204: OpenApiResponse(description="Deleted."), **BLOG_ERROR_RESPONSES},
    ),
)
class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly)
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Post]:
        queryset = Post.objects.select_related("author", "category").prefetch_related("tags")
        user = self.request.user
        if user.is_authenticated:
            return queryset.filter(status=Post.Status.PUBLISHED) | queryset.filter(author=user)
        return queryset.filter(status=Post.Status.PUBLISHED)

    def get_permissions(self) -> list[object]:
        if self.action == "comments" and self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def list(self, request: Request, *args: object, **kwargs: object) -> Response:
        language = getattr(request, "active_language", "en")
        user_timezone = getattr(request.user, "timezone", "UTC") if request.user.is_authenticated else "UTC"
        cache_key = f"{POST_LIST_CACHE_PREFIX}:{language}:{user_timezone}:{request.get_full_path()}"
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info("Returning cached published posts list.")
            return Response(cached_data)

        # Manual caching keeps pagination metadata and lets writes invalidate all post-list keys.
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, POST_LIST_CACHE_TIMEOUT)
        return response

    @method_decorator(ratelimit(key="user", rate=POST_CREATE_RATE, method="POST", block=False))
    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        if getattr(request, "limited", False):
            logger.info("Post creation rate limit exceeded for user ID: %s", request.user.id)
            return rate_limited_response()

        logger.info("Post creation attempt by user ID: %s", request.user.id)
        try:
            response = super().create(request, *args, **kwargs)
        except Exception:
            logger.exception("Post creation failed for user ID: %s", request.user.id)
            raise

        invalidate_post_list_cache()
        publish_post_if_needed(self.created_post)
        logger.info("Post created by user ID: %s", request.user.id)
        return response

    def perform_create(self, serializer: PostSerializer) -> None:
        self.created_post = serializer.save(author=self.request.user)

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        logger.info("Post update attempt by user ID: %s", request.user.id)
        previous_status = self.get_object().status
        try:
            response = super().update(request, *args, **kwargs)
        except Exception:
            logger.exception("Post update failed by user ID: %s", request.user.id)
            raise

        invalidate_post_list_cache()
        publish_post_if_needed(self.updated_post, previous_status)
        logger.info("Post updated by user ID: %s", request.user.id)
        return response

    def perform_update(self, serializer: PostSerializer) -> None:
        self.updated_post = serializer.save()

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        logger.info("Post deletion attempt by user ID: %s", request.user.id)
        try:
            response = super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception("Post deletion failed by user ID: %s", request.user.id)
            raise

        invalidate_post_list_cache()
        logger.info("Post deleted by user ID: %s", request.user.id)
        return response

    @extend_schema(
        summary="List or create post comments",
        description=(
            "GET lists comments for a published post and needs no authentication. POST creates a comment, requires authentication, "
            "and dispatches a Celery task that creates notifications and publishes a WebSocket message."
        ),
        tags=["Comments"],
        request=CommentSerializer,
        responses={200: CommentSerializer, 201: CommentSerializer, **BLOG_ERROR_RESPONSES},
        examples=[
            OpenApiExample("Comment request", value={"body": "Useful post."}, request_only=True),
            OpenApiExample("Comment response", value={"id": 1, "body": "Useful post."}, response_only=True),
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = self.get_object()
        if request.method == "GET":
            comments = post.comments.select_related("author")
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        serializer = CommentSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            comment = serializer.save(post=post, author=request.user)
        except Exception:
            logger.exception("Comment creation failed for post slug: %s", post.slug)
            raise

        dispatch_task(process_new_comment, comment.id)

        logger.info("Comment created for post slug: %s by user ID: %s", post.slug, request.user.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="List comments",
        description="Lists comments for published posts. Authentication is not required.",
        tags=["Comments"],
        responses={200: CommentSerializer, **BLOG_ERROR_RESPONSES},
    ),
    retrieve=extend_schema(
        summary="Get comment",
        description="Returns one comment on a published post. Authentication is not required.",
        tags=["Comments"],
        responses={200: CommentSerializer, **BLOG_ERROR_RESPONSES},
    ),
    partial_update=extend_schema(
        summary="Update own comment",
        description="Partially updates a comment. Authentication is required and only the author can update it.",
        tags=["Comments"],
        request=CommentSerializer,
        responses={200: CommentSerializer, **BLOG_ERROR_RESPONSES},
    ),
    update=extend_schema(
        summary="Replace own comment",
        description="Replaces a comment. Authentication is required and only the author can replace it.",
        tags=["Comments"],
        request=CommentSerializer,
        responses={200: CommentSerializer, **BLOG_ERROR_RESPONSES},
    ),
    destroy=extend_schema(
        summary="Delete own comment",
        description="Deletes a comment. Authentication is required and only the author can delete it.",
        tags=["Comments"],
        responses={204: OpenApiResponse(description="Deleted."), **BLOG_ERROR_RESPONSES},
    ),
)
class CommentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly)

    def get_queryset(self) -> QuerySet[Comment]:
        return Comment.objects.select_related("author", "post").filter(post__status=Post.Status.PUBLISHED)

    def update(self, request: Request, *args: object, **kwargs: object) -> Response:
        logger.info("Comment update attempt by user ID: %s", request.user.id)
        try:
            response = super().update(request, *args, **kwargs)
        except Exception:
            logger.exception("Comment update failed by user ID: %s", request.user.id)
            raise
        logger.info("Comment updated by user ID: %s", request.user.id)
        return response

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        logger.info("Comment deletion attempt by user ID: %s", request.user.id)
        try:
            response = super().destroy(request, *args, **kwargs)
        except Exception:
            logger.exception("Comment deletion failed by user ID: %s", request.user.id)
            raise
        logger.info("Comment deleted by user ID: %s", request.user.id)
        return response
