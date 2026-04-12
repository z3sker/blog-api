# Blog API

## ERD

![ERD](docs/erd.svg)

## Setup (Local)

1. Create `settings/.env` (see `settings/.env.example`)
2. Install deps: `pip install -r requirements/dev.txt`
3. Run migrations: `python manage.py migrate`
4. Start server: `python manage.py runserver`

Redis is required for caching, rate limiting, and pub/sub.

## API

Auth:
- `POST /api/auth/register/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`

Posts:
- `GET /api/posts/`
- `POST /api/posts/`
- `GET /api/posts/{slug}/`
- `PATCH /api/posts/{slug}/`
- `DELETE /api/posts/{slug}/`
- `GET /api/posts/{slug}/comments/`
- `POST /api/posts/{slug}/comments/`

Comments:
- `PATCH /api/comments/{id}/`
- `DELETE /api/comments/{id}/`

## Redis Pub/Sub

Listen for new comment events:
- `python manage.py listen_comments`
