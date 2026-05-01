from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.blog.streaming import post_publication_stream
from apps.blog.views import CategoryViewSet, CommentViewSet, PostViewSet, TagViewSet


router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("tags", TagViewSet, basename="tags")
router.register("posts", PostViewSet, basename="posts")
router.register("comments", CommentViewSet, basename="comments")

urlpatterns = [
    path("posts/stream/", post_publication_stream, name="post_publication_stream"),
    path("", include(router.urls)),
]
