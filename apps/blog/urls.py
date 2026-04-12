from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .stats import StatsView
from .views import CategoryViewSet, CommentViewSet, PostViewSet, TagViewSet

router = SimpleRouter()
router.register("posts", PostViewSet, basename="posts")
router.register("categories", CategoryViewSet, basename="categories")
router.register("tags", TagViewSet, basename="tags")
router.register("comments", CommentViewSet, basename="comments")

urlpatterns = [
    path("stats/", StatsView.as_view(), name="stats"),
    path("", include(router.urls)),
]
