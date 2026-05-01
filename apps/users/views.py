from __future__ import annotations

import logging

from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.tasks import dispatch_task
from apps.users.serializers import (
    LanguagePreferenceSerializer,
    LoggingTokenObtainPairSerializer,
    RegisterSerializer,
    TimezonePreferenceSerializer,
    UserSerializer,
)
from apps.users.tasks import send_welcome_email_task


logger = logging.getLogger("users")

REGISTER_RATE = "5/m"
TOKEN_RATE = "10/m"
TOO_MANY_REQUESTS_DETAIL = "Too many requests. Try again later."


def rate_limited_response() -> Response:
    return Response({"detail": _(TOO_MANY_REQUESTS_DETAIL)}, status=status.HTTP_429_TOO_MANY_REQUESTS)


AUTH_ERROR_RESPONSES = {
    400: OpenApiResponse(description="Validation error."),
    401: OpenApiResponse(description="Authentication credentials were invalid or missing."),
    403: OpenApiResponse(description="Permission denied."),
    404: OpenApiResponse(description="Endpoint not found."),
    429: OpenApiResponse(description=TOO_MANY_REQUESTS_DETAIL),
}


@extend_schema_view(
    create=extend_schema(
        summary="Register a user",
        description=(
            "Creates a user account, stores the selected language and timezone, sends a localized welcome email "
            "through the console email backend in local development, and returns a JWT token pair. "
            "Authentication is not required. Rate limit: 5 requests per minute per IP."
        ),
        tags=["Auth"],
        request=RegisterSerializer,
        responses={201: RegisterSerializer, **AUTH_ERROR_RESPONSES},
        examples=[
            OpenApiExample(
                "Register request",
                value={
                    "email": "writer@example.com",
                    "first_name": "Dana",
                    "last_name": "Writer",
                    "password": "strong-pass-123",
                    "password_confirm": "strong-pass-123",
                    "language": "en",
                    "timezone": "Asia/Almaty",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Register response",
                value={"user": {"id": 1, "email": "writer@example.com"}, "tokens": {"access": "...", "refresh": "..."}},
                response_only=True,
            ),
        ],
    )
)
@method_decorator(ratelimit(key="ip", rate=REGISTER_RATE, method="POST", block=False), name="dispatch")
class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request: Request, *args: object, **kwargs: object) -> Response:
        email = request.data.get("email")
        logger.info("Registration attempt for email: %s", email)
        if getattr(request, "limited", False):
            logger.info("Registration rate limit exceeded for email: %s", email)
            return rate_limited_response()

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except Exception:
            logger.exception("Registration failed for email: %s", email)
            raise

        dispatch_task(send_welcome_email_task, user.id)
        logger.info("User registered: %s", user.email)
        return Response(serializer.to_representation(user), status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key="ip", rate=TOKEN_RATE, method="POST", block=False), name="dispatch")
class LoggingTokenObtainPairView(TokenObtainPairView):
    serializer_class = LoggingTokenObtainPairSerializer

    @extend_schema(
        summary="Get JWT token pair",
        description=(
            "Authenticates a user by email and password and returns access and refresh tokens. "
            "Authentication is not required. The active language only affects translated error messages. "
            "Rate limit: 10 requests per minute per IP."
        ),
        tags=["Auth"],
        request=LoggingTokenObtainPairSerializer,
        responses={200: LoggingTokenObtainPairSerializer, **AUTH_ERROR_RESPONSES},
        examples=[
            OpenApiExample("Login request", value={"email": "writer@example.com", "password": "strong-pass-123"}, request_only=True),
            OpenApiExample("Login response", value={"access": "...", "refresh": "..."}, response_only=True),
        ],
    )
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        if getattr(request, "limited", False):
            logger.info("Login rate limit exceeded from IP.")
            return rate_limited_response()
        return super().post(request, *args, **kwargs)


class LanguagePreferenceView(views.APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Update language preference",
        description=(
            "Saves the authenticated user's preferred language. Future authenticated requests use this saved value "
            "before query parameters or Accept-Language headers. Authentication is required."
        ),
        tags=["Auth"],
        request=LanguagePreferenceSerializer,
        responses={200: UserSerializer, **AUTH_ERROR_RESPONSES},
        examples=[
            OpenApiExample("Language request", value={"language": "ru"}, request_only=True),
            OpenApiExample("Language response", value={"detail": "Language preference updated.", "user": {"language": "ru"}}, response_only=True),
        ],
    )
    def patch(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = LanguagePreferenceSerializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Language preference updated for user: %s", user.email)
        return Response({"detail": _("Language preference updated."), "user": UserSerializer(user).data})


class TimezonePreferenceView(views.APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Update timezone preference",
        description=(
            "Saves the authenticated user's IANA timezone. Future post responses are converted to this timezone "
            "and formatted with the active locale. Authentication is required."
        ),
        tags=["Auth"],
        request=TimezonePreferenceSerializer,
        responses={200: UserSerializer, **AUTH_ERROR_RESPONSES},
        examples=[
            OpenApiExample("Timezone request", value={"timezone": "Asia/Almaty"}, request_only=True),
            OpenApiExample("Timezone response", value={"detail": "Timezone preference updated.", "user": {"timezone": "Asia/Almaty"}}, response_only=True),
        ],
    )
    def patch(self, request: Request, *args: object, **kwargs: object) -> Response:
        serializer = TimezonePreferenceSerializer(instance=request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Timezone preference updated for user: %s", user.email)
        return Response({"detail": _("Timezone preference updated."), "user": UserSerializer(user).data})


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary="Refresh JWT access token",
        description=(
            "Accepts a refresh token and returns a new access token. Authentication is not required. "
            "The active language only affects translated error messages."
        ),
        tags=["Auth"],
        responses={200: OpenApiResponse(description="New access token."), **AUTH_ERROR_RESPONSES},
        examples=[
            OpenApiExample("Refresh request", value={"refresh": "..."}, request_only=True),
            OpenApiExample("Refresh response", value={"access": "..."}, response_only=True),
        ],
    )
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().post(request, *args, **kwargs)
