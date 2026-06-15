# Image de production du backend Django (ASGI : HTTP + websockets).
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# uv pour l'installation des dépendances.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Couche de dépendances (cache tant que pyproject/uv.lock ne changent pas).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Code applicatif.
COPY . .
RUN uv sync --frozen --no-dev

# Fichiers statiques (admin + Swagger) servis par WhiteNoise.
RUN DJANGO_SECRET_KEY=build-only uv run python manage.py collectstatic --noinput

RUN chmod +x /app/entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
