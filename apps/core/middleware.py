from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone, translation

from .constants import QUERY_PARAM_LANG, SUPPORTED_LANGUAGES

logger = logging.getLogger("core")


class LanguageTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = self._resolve_language(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language

        self._activate_timezone(request)
        response = self.get_response(request)
        response.headers["Content-Language"] = language
        translation.deactivate()
        timezone.deactivate()
        return response

    def _resolve_language(self, request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            user_lang = getattr(user, "language", None)
            if user_lang in SUPPORTED_LANGUAGES:
                return user_lang

        query_lang = request.GET.get(QUERY_PARAM_LANG)
        if query_lang in SUPPORTED_LANGUAGES:
            return query_lang

        header_lang = translation.get_language_from_request(request, check_path=False)
        if header_lang:
            normalized = header_lang.split("-")[0]
            if normalized in SUPPORTED_LANGUAGES:
                return normalized

        return settings.LANGUAGE_CODE

    def _activate_timezone(self, request: HttpRequest) -> None:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            timezone.activate(ZoneInfo("UTC"))
            return

        tz = getattr(user, "timezone", None)
        if not tz:
            timezone.activate(ZoneInfo("UTC"))
            return

        try:
            timezone.activate(ZoneInfo(tz))
        except Exception:
            logger.warning("Invalid timezone stored for user_id=%s", getattr(user, "id", None))
            timezone.activate(ZoneInfo("UTC"))
