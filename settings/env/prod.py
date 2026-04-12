from __future__ import annotations

from ..base import *  # noqa: F403
from ..conf import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}
