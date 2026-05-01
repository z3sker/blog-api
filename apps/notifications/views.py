from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework import status, views
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


NOTIFICATION_RESPONSES = {
    400: OpenApiResponse(description="Validation error."),
    401: OpenApiResponse(description="Authentication credentials were invalid or missing."),
    403: OpenApiResponse(description="Permission denied."),
    404: OpenApiResponse(description="Endpoint not found."),
}


class NotificationCountResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkNotificationsReadResponseSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField()


class NotificationListView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="List notifications",
        description=(
            "Lists notifications for the authenticated user. This endpoint supports HTTP polling clients "
            "that need periodic state without keeping a persistent connection open."
        ),
        tags=["Notifications"],
        responses={200: NotificationSerializer, **NOTIFICATION_RESPONSES},
        examples=[OpenApiExample("Notification response", value={"count": 1, "results": [{"id": 1, "is_read": False}]}, response_only=True)],
    )
    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Notification.objects.select_related("comment", "comment__post", "comment__author").filter(recipient=self.request.user)


class NotificationCountView(views.APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationCountResponseSerializer

    @extend_schema(
        summary="Get unread notification count",
        description=(
            "Returns the current user's unread notification count. Polling is simple and robust, but it adds latency "
            "and repeated server requests; use it for lightweight counters, and switch to SSE or WebSockets for instant streams."
        ),
        tags=["Notifications"],
        responses={200: NotificationCountResponseSerializer, **NOTIFICATION_RESPONSES},
        examples=[OpenApiExample("Count response", value={"unread_count": 3}, response_only=True)],
    )
    def get(self, request: Request, *args: object, **kwargs: object) -> Response:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": unread_count})


class MarkNotificationsReadView(views.APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MarkNotificationsReadResponseSerializer

    @extend_schema(
        summary="Mark notifications read",
        description="Marks all notifications for the authenticated user as read. Authentication is required.",
        tags=["Notifications"],
        responses={
            200: MarkNotificationsReadResponseSerializer,
            **NOTIFICATION_RESPONSES,
        },
        examples=[OpenApiExample("Read response", value={"updated_count": 3}, response_only=True)],
    )
    def post(self, request: Request, *args: object, **kwargs: object) -> Response:
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)
