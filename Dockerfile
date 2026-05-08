FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

WORKDIR /app/backend

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
RUN python -m pip install --upgrade pip && python -m pip install .

COPY docker/entrypoint-api.sh /entrypoint-api.sh
COPY docker/entrypoint-worker.sh /entrypoint-worker.sh
RUN chmod +x /entrypoint-api.sh /entrypoint-worker.sh

EXPOSE 8000
CMD ["/entrypoint-api.sh"]
