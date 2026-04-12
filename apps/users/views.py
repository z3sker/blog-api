from __future__ import annotations

import logging
from typing import Any

from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils.decorators import method_decorator

from apps.core.serializers import ErrorDetailSerializer

from .constants import RATE_LIMIT_REGISTER, RATE_LIMIT_TOKEN, TOO_MANY_REQUESTS_DETAIL
from .serializers import (
    LanguageUpdateSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    TimezoneUpdateSerializer,
    UserSerializer,
)
from .services import send_welcome_email

logger = logging.getLogger("users")


def too_many_requests() -> Response:
    return Response({"detail": TOO_MANY_REQUESTS_DETAIL}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @method_decorator(ratelimit(key="ip", rate=RATE_LIMIT_REGISTER, method="POST", block=False))
    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        description=(
            "Creates a new user account and returns the created user plus a JWT token pair. "
            "Rate-limited per IP. Sends a welcome email rendered from templates in the selected language."
        ),
        request=RegisterSerializer,
        responses={
            201: RegisterResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
            429: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request",
                value={
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "language": "ru",
                    "password": "strongpassword",
                    "password2": "strongpassword",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "language": "ru",
                        "timezone": "UTC",
                        "avatar": None,
                        "date_joined": "2026-04-12T12:00:00Z",
                    },
                    "access": "<jwt-access>",
                    "refresh": "<jwt-refresh>",
                },
                response_only=True,
            ),
        ],
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        logger.info("Registration attempt for email: %s", request.data.get("email"))
        if getattr(request, "limited", False):
            logger.warning("Registration rate limit exceeded for ip")
            return too_many_requests()

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Registration failed for email: %s", request.data.get("email"))
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        logger.info("User registered: %s", user.email)
        try:
            send_welcome_email(to_email=user.email, first_name=user.first_name, language=user.language)
        except Exception:
            logger.exception("Welcome email send failed for %s", user.email)
        payload = RegisterResponseSerializer.build(user)
        return Response(payload, status=status.HTTP_201_CREATED)


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    @method_decorator(ratelimit(key="ip", rate=RATE_LIMIT_TOKEN, method="POST", block=False))
    @extend_schema(
        tags=["Auth"],
        summary="Obtain token pair",
        description=(
            "Returns a JWT access/refresh token pair for valid credentials. "
            "Rate-limited per IP."
        ),
        responses={
            200: OpenApiResponse(description="Token pair"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Invalid credentials"),
            429: ErrorDetailSerializer,
        },
        examples=[
            OpenApiExample(
                "Request",
                value={"email": "user@example.com", "password": "strongpassword"},
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={"access": "<jwt-access>", "refresh": "<jwt-refresh>"},
                response_only=True,
            ),
        ],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email = request.data.get("email")
        logger.info("Login attempt for email: %s", email)
        if getattr(request, "limited", False):
            logger.warning("Login rate limit exceeded for ip")
            return too_many_requests()

        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info("Login success for email: %s", email)
        else:
            logger.warning("Login failed for email: %s", email)
        return response


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        description="Returns a new JWT access token using a refresh token.",
        responses={200: OpenApiResponse(description="New access token"), 400: OpenApiResponse(description="Validation error")},
        examples=[
            OpenApiExample("Request", value={"refresh": "<jwt-refresh>"}, request_only=True),
            OpenApiExample("Response", value={"access": "<jwt-access>"}, response_only=True),
        ],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)


class UserPreferencesViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return None

    def _response(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    @method_decorator(ratelimit(key="user", rate="30/m", method="PATCH", block=False))
    @extend_schema(
        tags=["Auth"],
        summary="Update preferred language",
        description=(
            "Updates the authenticated user's preferred language. "
            "This preference takes priority when resolving request language."
        ),
        request=LanguageUpdateSerializer,
        responses={200: UserSerializer, 400: OpenApiResponse(description="Validation error"), 401: OpenApiResponse(description="Unauthorized")},
        examples=[
            OpenApiExample("Request", value={"language": "kk"}, request_only=True),
            OpenApiExample(
                "Response",
                value={
                    "id": 1,
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "language": "kk",
                    "timezone": "UTC",
                    "avatar": None,
                    "date_joined": "2026-04-12T12:00:00Z",
                },
                response_only=True,
            ),
        ],
    )
    def language(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = LanguageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.language = serializer.validated_data["language"]
        request.user.save(update_fields=["language"])
        logger.info("User language updated user_id=%s lang=%s", request.user.id, request.user.language)
        return self._response(request)

    @method_decorator(ratelimit(key="user", rate="30/m", method="PATCH", block=False))
    @extend_schema(
        tags=["Auth"],
        summary="Update preferred timezone",
        description=(
            "Updates the authenticated user's preferred timezone (IANA identifier). "
            "Timezone is activated for every authenticated request and used for local date formatting."
        ),
        request=TimezoneUpdateSerializer,
        responses={200: UserSerializer, 400: OpenApiResponse(description="Validation error"), 401: OpenApiResponse(description="Unauthorized")},
        examples=[
            OpenApiExample("Request", value={"timezone": "Asia/Almaty"}, request_only=True),
            OpenApiExample(
                "Response",
                value={
                    "id": 1,
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "language": "en",
                    "timezone": "Asia/Almaty",
                    "avatar": None,
                    "date_joined": "2026-04-12T12:00:00Z",
                },
                response_only=True,
            ),
        ],
    )
    def timezone(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = TimezoneUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.timezone = serializer.validated_data["timezone"]
        request.user.save(update_fields=["timezone"])
        logger.info("User timezone updated user_id=%s tz=%s", request.user.id, request.user.timezone)
        return self._response(request)
