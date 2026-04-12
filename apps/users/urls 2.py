from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RateLimitedTokenObtainPairView, RegisterViewSet

router = SimpleRouter()
router.register("register", RegisterViewSet, basename="register")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", RateLimitedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
