from __future__ import annotations

import logging
from zoneinfo import available_timezones

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _

from apps.core.i18n import DEFAULT_LANGUAGE, DEFAULT_TIMEZONE
from apps.users.models import User, UserLanguage


logger = logging.getLogger("users")

PASSWORD_MIN_LENGTH = 8


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "avatar", "date_joined", "language", "timezone")
        read_only_fields = ("id", "date_joined")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, min_length=PASSWORD_MIN_LENGTH)
    password_confirm = serializers.CharField(write_only=True, min_length=PASSWORD_MIN_LENGTH)
    language = serializers.ChoiceField(choices=UserLanguage.choices, default=DEFAULT_LANGUAGE)
    timezone = serializers.CharField(default=DEFAULT_TIMEZONE)

    def validate_email(self, value: str) -> str:
        normalized_email = User.objects.normalize_email(value).lower()
        if User.objects.filter(email=normalized_email).exists():
            logger.info("Registration failed because email already exists: %s", normalized_email)
            raise serializers.ValidationError(_("A user with this email already exists."))
        return normalized_email

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError(_("Enter a valid IANA timezone."))
        return value

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if attrs["password"] != attrs["password_confirm"]:
            logger.info("Registration failed because passwords did not match for email: %s", attrs.get("email"))
            raise serializers.ValidationError({"password_confirm": _("Passwords do not match.")})
        return attrs

    def create(self, validated_data: dict[str, str]) -> User:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def to_representation(self, instance: User) -> dict[str, object]:
        refresh = RefreshToken.for_user(instance)
        return {
            "user": UserSerializer(instance).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        }


class LoggingTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        email = attrs.get(self.username_field)
        logger.info("Login attempt for email: %s", email)
        try:
            data = super().validate(attrs)
        except Exception:
            logger.info("Login failed for email: %s", email)
            raise

        logger.info("Login succeeded for email: %s", email)
        return data


class LanguagePreferenceSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=UserLanguage.choices)

    def update(self, instance: User, validated_data: dict[str, str]) -> User:
        instance.language = validated_data["language"]
        instance.save(update_fields=["language"])
        return instance


class TimezonePreferenceSerializer(serializers.Serializer):
    timezone = serializers.CharField()

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError(_("Enter a valid IANA timezone."))
        return value

    def update(self, instance: User, validated_data: dict[str, str]) -> User:
        instance.timezone = validated_data["timezone"]
        instance.save(update_fields=["timezone"])
        return instance
