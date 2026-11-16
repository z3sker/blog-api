from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

from apps.auths.constants import (
    EMAIL_REQUIRED_MESSAGE,
    SUPERUSER_STAFF_MESSAGE,
    SUPERUSER_SUPERUSER_MESSAGE,
)

if TYPE_CHECKING:
    from apps.auths.models import User


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError(EMAIL_REQUIRED_MESSAGE)
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(SUPERUSER_STAFF_MESSAGE)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(SUPERUSER_SUPERUSER_MESSAGE)
        return self._create_user(email, password, **extra_fields)
