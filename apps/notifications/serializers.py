from __future__ import annotations

from rest_framework import serializers

from apps.blog.serializers import CommentSerializer
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    comment = CommentSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ("id", "comment", "is_read", "created_at")
        read_only_fields = fields

