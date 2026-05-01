#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT_STEP="startup"
trap 'echo "Step failed: ${CURRENT_STEP}" >&2' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/settings/.env"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

REQUIRED_ENV_VARS=(
  "BLOG_ENV_ID"
  "BLOG_SECRET_KEY"
  "BLOG_ALLOWED_HOSTS"
  "BLOG_REDIS_URL"
  "BLOG_CELERY_BROKER_URL"
  "BLOG_FLOWER_USER"
  "BLOG_FLOWER_PASSWORD"
  "BLOG_SEED_DB"
)

SUPERUSER_EMAIL="admin@example.com"
SUPERUSER_PASSWORD="Adminpass123!"
SUPERUSER_FIRST_NAME="Admin"
SUPERUSER_LAST_NAME="User"

cd "${ROOT_DIR}"

CURRENT_STEP="checking environment variables"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing variable: settings/.env" >&2
  exit 1
fi

for variable in "${REQUIRED_ENV_VARS[@]}"; do
  value="$(grep -E "^${variable}=" "${ENV_FILE}" | tail -n 1 | cut -d '=' -f 2- | tr -d '"' | tr -d "'" || true)"
  if [[ -z "${value// }" ]]; then
    echo "Missing variable: ${variable}" >&2
    exit 1
  fi
done

CURRENT_STEP="creating virtual environment"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3.13 >/dev/null 2>&1; then
    python3.13 -m venv "${VENV_DIR}"
  else
    python3 -m venv "${VENV_DIR}"
  fi
fi

CURRENT_STEP="installing dependencies"
"${PIP_BIN}" install --upgrade pip
"${PIP_BIN}" install -r requirements/dev.txt

CURRENT_STEP="running migrations"
"${PYTHON_BIN}" manage.py migrate

CURRENT_STEP="collecting static files"
"${PYTHON_BIN}" manage.py collectstatic --noinput

CURRENT_STEP="compiling translation files"
"${PYTHON_BIN}" manage.py compilemessages

CURRENT_STEP="creating superuser"
"${PYTHON_BIN}" manage.py shell <<PY
from django.contrib.auth import get_user_model

User = get_user_model()
user, created = User.objects.get_or_create(
    email="${SUPERUSER_EMAIL}",
    defaults={
        "first_name": "${SUPERUSER_FIRST_NAME}",
        "last_name": "${SUPERUSER_LAST_NAME}",
        "is_staff": True,
        "is_superuser": True,
        "language": "en",
        "timezone": "UTC",
    },
)
if created:
    user.set_password("${SUPERUSER_PASSWORD}")
    user.save()
else:
    changed = False
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    if changed:
        user.save(update_fields=["is_staff", "is_superuser"])
print("Superuser is ready.")
PY

CURRENT_STEP="seeding database"
"${PYTHON_BIN}" manage.py seed

cat <<SUMMARY

Project is ready.
API:        http://127.0.0.1:8000/api/
Swagger:    http://127.0.0.1:8000/api/docs/
ReDoc:      http://127.0.0.1:8000/api/redoc/
Admin:      http://127.0.0.1:8000/admin/

Superuser:
  email:    ${SUPERUSER_EMAIL}
  password: ${SUPERUSER_PASSWORD}

SUMMARY

CURRENT_STEP="starting development server"
exec "${PYTHON_BIN}" manage.py runserver 127.0.0.1:8000
