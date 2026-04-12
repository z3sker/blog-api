from __future__ import annotations

import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation

logger = logging.getLogger("users")

WELCOME_SUBJECT_TEMPLATE = "emails/welcome/subject.txt"
WELCOME_BODY_TEMPLATE = "emails/welcome/body.txt"


def send_welcome_email(*, to_email: str, first_name: str, language: str) -> None:
    with translation.override(language):
        subject = render_to_string(WELCOME_SUBJECT_TEMPLATE, {}).strip()
        body = render_to_string(WELCOME_BODY_TEMPLATE, {"first_name": first_name}).strip()
    email = EmailMultiAlternatives(subject=subject, body=body, to=[to_email])
    email.send(fail_silently=False)
    logger.info("Welcome email sent to %s (lang=%s)", to_email, language)
