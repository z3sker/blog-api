from __future__ import annotations

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation

from apps.users.models import User


WELCOME_SUBJECT_TEMPLATE = "emails/welcome/subject.txt"
WELCOME_BODY_TEMPLATE = "emails/welcome/body.txt"
DEFAULT_FROM_EMAIL = "noreply@blog-api.local"


def send_welcome_email(user: User) -> int:
    context = {"user": user}
    with translation.override(user.language):
        subject = "".join(render_to_string(WELCOME_SUBJECT_TEMPLATE, context).splitlines())
        body = render_to_string(WELCOME_BODY_TEMPLATE, context)

    return send_mail(subject, body, DEFAULT_FROM_EMAIL, [user.email])
