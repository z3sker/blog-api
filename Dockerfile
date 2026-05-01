FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/base.txt

COPY . .

RUN chmod +x scripts/entrypoint.sh scripts/start_flower.sh \
    && adduser --disabled-password --gecos "" django \
    && mkdir -p /app/logs /app/staticfiles /app/media /app/data \
    && chown -R django:django /app

USER django

ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "settings.asgi:application"]
