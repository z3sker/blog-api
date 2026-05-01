from __future__ import annotations

from celery import shared_task

from apps.users.emails import send_welcome_email
from apps.users.models import User


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email_task(user_id: int) -> int:
    # Retries matter for email because SMTP/backend outages are usually temporary and the welcome message should still go out.
    user = User.objects.get(id=user_id)
    return send_welcome_email(user)
