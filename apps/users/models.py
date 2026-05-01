from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.users.managers import UserManager
from apps.core.i18n import DEFAULT_LANGUAGE, DEFAULT_TIMEZONE


FIRST_NAME_MAX_LENGTH = 50
LAST_NAME_MAX_LENGTH = 50
AVATAR_UPLOAD_PATH = "avatars/"
LANGUAGE_MAX_LENGTH = 2
TIMEZONE_MAX_LENGTH = 64


class UserLanguage(models.TextChoices):
    ENGLISH = "en", _("English")
    RUSSIAN = "ru", _("Russian")
    KAZAKH = "kk", _("Kazakh")


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=FIRST_NAME_MAX_LENGTH)
    last_name = models.CharField(_("last name"), max_length=LAST_NAME_MAX_LENGTH)
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    avatar = models.ImageField(_("avatar"), upload_to=AVATAR_UPLOAD_PATH, blank=True, null=True)
    language = models.CharField(
        _("preferred language"),
        max_length=LANGUAGE_MAX_LENGTH,
        choices=UserLanguage.choices,
        default=DEFAULT_LANGUAGE,
    )
    timezone = models.CharField(_("timezone"), max_length=TIMEZONE_MAX_LENGTH, default=DEFAULT_TIMEZONE)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email
