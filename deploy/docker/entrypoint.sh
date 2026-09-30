#!/bin/sh
set -eu

if [ "$1" = "gunicorn" ]; then
    python -c 'import os; key = os.environ.get("SECRET_KEY", ""); assert len(key) >= 50 and key != "change-me", "Set a random SECRET_KEY of at least 50 characters"'
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
