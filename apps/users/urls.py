from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    DocumentedTokenRefreshView,
    RateLimitedTokenObtainPairView,
    RegisterViewSet,
    UserPreferencesViewSet,
)

router = SimpleRouter()
router.register("register", RegisterViewSet, basename="register")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "language/",
        UserPreferencesViewSet.as_view({"patch": "language"}),
        name="user_language",
    ),
    path(
        "timezone/",
        UserPreferencesViewSet.as_view({"patch": "timezone"}),
        name="user_timezone",
    ),
    path("token/", RateLimitedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", DocumentedTokenRefreshView.as_view(), name="token_refresh"),
]
