from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.http import HttpRequest, HttpResponse
from django.utils import timezone, translation
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.i18n import DEFAULT_LANGUAGE, DEFAULT_TIMEZONE, language_from_header, normalize_language


LANG_QUERY_PARAM = "lang"


class UserLocaleMiddleware:
    def __init__(self, get_response: object) -> None:
        self.get_response = get_response
        self.jwt_authentication = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = self.get_authenticated_user(request)
        language = self.resolve_language(request, user)
        user_timezone = getattr(user, "timezone", DEFAULT_TIMEZONE) if user else DEFAULT_TIMEZONE

        translation.activate(language)
        request.LANGUAGE_CODE = language
        request.active_language = language

        try:
            timezone.activate(ZoneInfo(user_timezone))
        except ZoneInfoNotFoundError:
            timezone.activate(ZoneInfo(DEFAULT_TIMEZONE))

        response = self.get_response(request)
        translation.deactivate()
        timezone.deactivate()
        return response

    def get_authenticated_user(self, request: HttpRequest) -> object | None:
        try:
            authenticated = self.jwt_authentication.authenticate(request)
        except Exception:
            return None
        if not authenticated:
            return None
        user, _token = authenticated
        request.user = user
        return user

    def resolve_language(self, request: HttpRequest, user: object | None) -> str:
        saved_language = getattr(user, "language", None)
        if saved_language:
            return normalize_language(saved_language)

        query_language = request.GET.get(LANG_QUERY_PARAM)
        if query_language:
            return normalize_language(query_language)

        header_language = request.META.get("HTTP_ACCEPT_LANGUAGE")
        if header_language:
            return language_from_header(header_language)

        return DEFAULT_LANGUAGE
