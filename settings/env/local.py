from __future__ import annotations

from settings.base import *  # noqa: F403
from settings.conf import SQLITE_PATH


DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_PATH,
    },
}
