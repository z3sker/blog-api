from __future__ import annotations

from pathlib import Path

from decouple import AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = AutoConfig(search_path=str(BASE_DIR / "settings"))

ENV_ID: str = CONFIG("BLOG_ENV_ID", default="local")

SECRET_KEY: str = CONFIG("BLOG_SECRET_KEY", default="django-insecure-change-me")
ALLOWED_HOSTS: list[str] = CONFIG(
    "BLOG_ALLOWED_HOSTS",
    cast=Csv(),
    default="localhost,127.0.0.1",
)

REDIS_URL: str = CONFIG("BLOG_REDIS_URL", default="redis://127.0.0.1:6379/1")
DEFAULT_FROM_EMAIL: str = CONFIG("BLOG_DEFAULT_FROM_EMAIL", default="no-reply@example.com")

DB_NAME: str = CONFIG("BLOG_DB_NAME", default="blog")
DB_USER: str = CONFIG("BLOG_DB_USER", default="postgres")
DB_PASSWORD: str = CONFIG("BLOG_DB_PASSWORD", default="postgres")
DB_HOST: str = CONFIG("BLOG_DB_HOST", default="127.0.0.1")
DB_PORT: int = CONFIG("BLOG_DB_PORT", cast=int, default=5432)
