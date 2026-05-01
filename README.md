# Blog API

Homework 1 implementation of a Django REST Framework blog API with email-based users, JWT auth, posts, comments, Redis caching, Redis-backed rate limiting, and Redis pub/sub for new comments.

## ERD

![Blog API ERD](docs/erd.svg)

## Local setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

Create or edit `settings/.env` for local values. Every project variable uses the `BLOG_` prefix.

Or run the full local setup script:

```bash
./scripts/start.sh
```

Docker:

```bash
docker compose up --build
```

## Main endpoints

- `POST /api/auth/register/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `PATCH /api/auth/language/`
- `PATCH /api/auth/timezone/`
- `GET /api/posts/`
- `POST /api/posts/`
- `GET /api/posts/{slug}/`
- `PATCH /api/posts/{slug}/`
- `DELETE /api/posts/{slug}/`
- `GET /api/posts/{slug}/comments/`
- `POST /api/posts/{slug}/comments/`
- `GET /api/posts/stream/`
- `GET /api/notifications/`
- `GET /api/notifications/count/`
- `POST /api/notifications/read/`
- `GET /api/stats/`

API docs:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`

Real-time:

- WebSocket comments: `ws://localhost:8000/ws/posts/{slug}/comments/?token=<access_token>`
- SSE published posts: `/api/posts/stream/`
- Flower: `http://localhost:5555`

## Redis

The app expects Redis at `BLOG_REDIS_URL`, defaulting to `redis://127.0.0.1:6379/1`.

New comments publish a JSON message to the `comments` channel. To listen:

```bash
python manage.py listen_comments
```
