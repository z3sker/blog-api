from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.views import DocumentedTokenRefreshView, LanguagePreferenceView, LoggingTokenObtainPairView, RegisterViewSet, TimezonePreferenceView


router = DefaultRouter()
router.register("register", RegisterViewSet, basename="register")

urlpatterns = [
    path("", include(router.urls)),
    path("language/", LanguagePreferenceView.as_view(), name="language_preference"),
    path("timezone/", TimezonePreferenceView.as_view(), name="timezone_preference"),
    path("token/", LoggingTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", DocumentedTokenRefreshView.as_view(), name="token_refresh"),
]
