from decouple import Csv, config

ENV_ID: str = config("BLOG_ENV_ID", default="local")
SECRET_KEY: str = config("BLOG_SECRET_KEY")
ALLOWED_HOSTS: list[str] = config("BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

DB_NAME: str = config("BLOG_DB_NAME", default="blog")
DB_USER: str = config("BLOG_DB_USER", default="blog")
DB_PASSWORD: str = config("BLOG_DB_PASSWORD", default="")
DB_HOST: str = config("BLOG_DB_HOST", default="localhost")
DB_PORT: int = config("BLOG_DB_PORT", default=5432, cast=int)

REDIS_URL: str = config("BLOG_REDIS_URL", default="redis://localhost:6379/0")
SQL_LOGGING: bool = config("BLOG_SQL_LOGGING", default=False, cast=bool)
