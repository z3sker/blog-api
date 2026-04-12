from __future__ import annotations

import logging
from typing import Any

from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.decorators import method_decorator

from .constants import RATE_LIMIT_REGISTER, RATE_LIMIT_TOKEN, TOO_MANY_REQUESTS_DETAIL
from .serializers import RegisterResponseSerializer, RegisterSerializer

logger = logging.getLogger("users")


def too_many_requests() -> Response:
    return Response({"detail": TOO_MANY_REQUESTS_DETAIL}, status=status.HTTP_429_TOO_MANY_REQUESTS)


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @method_decorator(ratelimit(key="ip", rate=RATE_LIMIT_REGISTER, method="POST", block=False))
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
        payload = RegisterResponseSerializer.build(user)
        return Response(payload, status=status.HTTP_201_CREATED)


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    @method_decorator(ratelimit(key="ip", rate=RATE_LIMIT_TOKEN, method="POST", block=False))
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
