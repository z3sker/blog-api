from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.blog.models import Comment


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="notifications")
    is_read = models.BooleanField(_("read"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        constraints = [
            models.UniqueConstraint(fields=["recipient", "comment"], name="unique_notification_per_comment_recipient"),
        ]

    def __str__(self) -> str:
        return f"Notification {self.id} for {self.recipient_id}"

