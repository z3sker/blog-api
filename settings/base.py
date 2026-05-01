from __future__ import annotations

import os

from settings.conf import ALLOWED_HOSTS as CONF_ALLOWED_HOSTS
from settings.conf import BASE_DIR, CELERY_BROKER_URL as CONF_CELERY_BROKER_URL
from settings.conf import REDIS_URL
from settings.conf import SECRET_KEY as CONF_SECRET_KEY


DEBUG = False
SECRET_KEY = CONF_SECRET_KEY
ALLOWED_HOSTS = CONF_ALLOWED_HOSTS

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "apps.core",
    "apps.users",
    "apps.blog",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.UserLocaleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"
ASGI_APPLICATION = "settings.asgi.application"

AUTH_USER_MODEL = "users.User"

LANGUAGE_CODE = "en"
LANGUAGES = (
    ("en", "English"),
    ("ru", "Russian"),
    ("kk", "Kazakh"),
)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "PAGE_SIZE": 10,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Blog API",
    "DESCRIPTION": "Django REST API for a multilingual blog.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "APPEND_PATHS": {
        "/api/stats/": {
            "get": {
                "operationId": "stats_retrieve",
                "summary": "Get blog statistics",
                "description": (
                    "Returns public blog counts together with exchange rates and current Almaty time. "
                    "Authentication is not required. The two external API calls run concurrently with asyncio.gather. "
                    "No Redis cache is written and no database rows are changed."
                ),
                "tags": ["Stats"],
                "responses": {
                    "200": {
                        "description": "Stats response.",
                        "content": {
                            "application/json": {
                                "example": {
                                    "blog": {"total_posts": 42, "total_comments": 137, "total_users": 15},
                                    "exchange_rates": {"KZT": 450.23, "RUB": 89.10, "EUR": 0.92},
                                    "current_time": "2024-03-15T18:30:00+05:00",
                                }
                            }
                        },
                    },
                    "400": {"description": "Bad request."},
                    "401": {"description": "Authentication credentials were invalid."},
                    "403": {"description": "Permission denied."},
                    "404": {"description": "Endpoint not found."},
                },
            }
        },
        "/api/posts/stream/": {
            "get": {
                "operationId": "posts_stream_retrieve",
                "summary": "Stream published posts",
                "description": (
                    "Streams newly published posts as Server-Sent Events. Authentication is not required. "
                    "The response uses text/event-stream and stays open while events are published."
                ),
                "tags": ["Posts"],
                "responses": {
                    "200": {
                        "description": "SSE stream of published post events.",
                        "content": {
                            "text/event-stream": {
                                "example": (
                                    "data: {\"post_id\": 1, \"title\": \"First Post\", "
                                    "\"slug\": \"first-post\", \"author\": {\"id\": 1, "
                                    "\"email\": \"writer@example.com\"}, "
                                    "\"published_at\": \"2026-05-02T10:00:00+05:00\"}\\n\\n"
                                )
                            }
                        },
                    },
                    "400": {"description": "Bad request."},
                    "401": {"description": "Authentication credentials were invalid."},
                    "403": {"description": "Permission denied."},
                    "404": {"description": "Endpoint not found."},
                },
            }
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = CONF_CELERY_BROKER_URL
CELERY_RESULT_BACKEND = CONF_CELERY_BROKER_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "verbose": {
            "format": "{asctime} {levelname} {name} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "formatter": "verbose",
            "filename": LOG_DIR / "app.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
        },
        "debug_requests": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "verbose",
            "filename": LOG_DIR / "debug_requests.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "filters": ["require_debug_true"],
        },
    },
    "loggers": {
        "users": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "blog": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file", "debug_requests"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
