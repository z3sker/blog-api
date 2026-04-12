from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from zoneinfo import available_timezones

from .models import LANGUAGE_CHOICES

logger = logging.getLogger("users")
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "language",
            "timezone",
            "avatar",
            "date_joined",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, default="en")
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password2"]:
            logger.debug("Password mismatch during registration for email: %s", attrs.get("email"))
            raise serializers.ValidationError({"password2": _("Passwords do not match.")})
        return attrs

    def create(self, validated_data: dict):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        logger.debug("User created via serializer: %s", user.email)
        return user


class RegisterResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()

    @classmethod
    def build(cls, user) -> dict:
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class LanguageUpdateSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES)


class TimezoneUpdateSerializer(serializers.Serializer):
    timezone = serializers.CharField(max_length=64)

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError(_("Invalid timezone. Use a valid IANA timezone name."))
        return value
