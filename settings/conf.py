from __future__ import annotations

from pathlib import Path

from decouple import AutoConfig, Csv


BASE_DIR = Path(__file__).resolve().parent.parent
config = AutoConfig(search_path=str(BASE_DIR / "settings"))

BLOG_ENV_ID = config("BLOG_ENV_ID", default="local")
SECRET_KEY = config("BLOG_SECRET_KEY", default="unsafe-dev-secret-key")
ALLOWED_HOSTS = config("BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
REDIS_URL = config("BLOG_REDIS_URL", default="redis://127.0.0.1:6379/1")
CELERY_BROKER_URL = config("BLOG_CELERY_BROKER_URL", default="redis://127.0.0.1:6379/2")
FLOWER_USER = config("BLOG_FLOWER_USER", default="admin")
FLOWER_PASSWORD = config("BLOG_FLOWER_PASSWORD", default="changeme")
SEED_DB = config("BLOG_SEED_DB", default=False, cast=bool)
SQLITE_PATH = config("BLOG_SQLITE_PATH", default=str(BASE_DIR / "db.sqlite3"))
DATABASE_URL = config("BLOG_DATABASE_URL", default="")
