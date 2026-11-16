# Blog API

A blog REST API built with Django and Django REST Framework.

## ERD

![ERD](docs/erd.png)

## Project structure

```
blog-api/
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── logs/
├── apps/
│   ├── auths/          custom user model, JWT authentication
│   └── blog/           posts, comments, categories, tags
├── docs/
└── settings/
    ├── .env            secrets (not committed)
    ├── .env.example
    ├── conf.py         reads .env with python-decouple
    ├── base.py         shared settings
    ├── urls.py
    ├── wsgi.py
    ├── asgi.py
    └── env/
        ├── local.py    DEBUG=True, SQLite
        └── prod.py     DEBUG=False, PostgreSQL
```

`manage.py` reads `BLOG_ENV_ID` from `settings/.env` and uses `settings.env.<BLOG_ENV_ID>`
as `DJANGO_SETTINGS_MODULE`.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp settings/.env.example settings/.env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Set `BLOG_SECRET_KEY` in `settings/.env` to a long random string.

## Environment variables

| Variable             | Description                                   |
|----------------------|-----------------------------------------------|
| `BLOG_ENV_ID`        | `local` or `prod`                             |
| `BLOG_SECRET_KEY`    | Django secret key                             |
| `BLOG_ALLOWED_HOSTS` | Comma-separated list of hosts                 |
| `BLOG_DB_*`          | PostgreSQL connection for `prod`              |
| `BLOG_REDIS_URL`     | Redis connection URL                          |
| `BLOG_SQL_LOGGING`   | `True` prints every SQL query in `local`      |

## Authentication

Login uses email instead of username. JWT tokens:

- `POST /api/auth/token/` with `email` and `password`
- `POST /api/auth/token/refresh/` with `refresh`

## Linting

```bash
ruff check .
ruff format .
```
