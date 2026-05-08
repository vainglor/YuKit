#!/bin/sh
set -eu

cd /app/backend
if [ -n "${YUKIT_DATABASE_URL:-}" ]; then
  alembic upgrade head
fi
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
