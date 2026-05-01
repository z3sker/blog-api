from __future__ import annotations

import dj_database_url

from settings.base import *  # noqa: F403
from settings.conf import DATABASE_URL


DEBUG = False

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )
}

