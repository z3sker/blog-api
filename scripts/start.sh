#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

ENV_FILE="settings/.env"

required_env_vars=(
  "BLOG_ENV_ID"
  "BLOG_SECRET_KEY"
  "BLOG_ALLOWED_HOSTS"
  "BLOG_REDIS_URL"
  "BLOG_DEFAULT_FROM_EMAIL"
)

step() {
  echo "==> $1"
}

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

run_step() {
  local name="$1"
  shift
  step "$name"
  "$@" || fail "$name failed"
}

step "Validate env"
[ -f "$ENV_FILE" ] || fail "Missing env file: $ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
missing=0
for v in "${required_env_vars[@]}"; do
  if [ -z "${!v:-}" ]; then
    echo "Missing or empty: $v"
    missing=1
  fi
done
[ "$missing" -eq 0 ] || exit 1

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d ".venv" ]; then
  run_step "Create venv" "$PYTHON_BIN" -m venv .venv
fi

run_step "Install deps" bash -c '. .venv/bin/activate && pip install -r requirements/dev.txt'
run_step "Migrate" bash -c '. .venv/bin/activate && python manage.py migrate'
run_step "Collect static" bash -c '. .venv/bin/activate && python manage.py collectstatic --noinput'
run_step "Compile translations" bash -c '. .venv/bin/activate && python manage.py compilemessages'

ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="admin12345"

run_step "Create superuser" bash -c '
  . .venv/bin/activate
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = \"'"$ADMIN_EMAIL"'\".lower()
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=\"'"$ADMIN_PASSWORD"'\", first_name=\"Admin\", last_name=\"User\", language=\"en\", timezone=\"UTC\")
print(\"superuser_ok\")
"
'

run_step "Seed data" bash -c '. .venv/bin/activate && python manage.py seed_data'

step "Start server"
. .venv/bin/activate
python manage.py runserver 0.0.0.0:8000 &
server_pid=$!
sleep 1

echo ""
echo "API:        http://127.0.0.1:8000/api/"
echo "Swagger UI: http://127.0.0.1:8000/api/docs/"
echo "ReDoc:      http://127.0.0.1:8000/api/redoc/"
echo "Schema:     http://127.0.0.1:8000/api/schema/"
echo "Admin:      http://127.0.0.1:8000/admin/"
echo ""
echo "Superuser:"
echo "  email:    $ADMIN_EMAIL"
echo "  password: $ADMIN_PASSWORD"
echo ""

wait "$server_pid"
