from __future__ import annotations

from django.urls import path

from apps.notifications.views import MarkNotificationsReadView, NotificationCountView, NotificationListView


urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("count/", NotificationCountView.as_view(), name="notification_count"),
    path("read/", MarkNotificationsReadView.as_view(), name="notification_read"),
]

