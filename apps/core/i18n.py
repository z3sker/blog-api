from __future__ import annotations

from django.conf import settings
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = tuple(language_code for language_code, _language_name in settings.LANGUAGES)
SUPPORTED_LANGUAGE_SET = set(SUPPORTED_LANGUAGES)
DEFAULT_TIMEZONE = "UTC"


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    language_code = language.lower().split("-", 1)[0]
    if language_code in SUPPORTED_LANGUAGE_SET:
        return language_code
    return DEFAULT_LANGUAGE


def language_from_header(header_value: str | None) -> str:
    if not header_value:
        return DEFAULT_LANGUAGE
    for language_range in header_value.split(","):
        language = language_range.split(";", 1)[0].strip().lower().split("-", 1)[0]
        if language in SUPPORTED_LANGUAGE_SET:
            return language
    return DEFAULT_LANGUAGE
