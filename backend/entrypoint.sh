#!/bin/sh
# Point d'entrée du conteneur backend : applique les migrations puis lance
# le process demandé (web par défaut, ou worker/beat Celery).
set -e

ROLE="${1:-web}"

case "$ROLE" in
  web)
    python manage.py migrate --noinput
    # gunicorn + worker uvicorn : sert HTTP et websockets /ws/ dans un seul process.
    exec gunicorn config.asgi:application \
      -k uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-2}"
    ;;
  worker)
    exec celery -A config worker --loglevel=info
    ;;
  beat)
    exec celery -A config beat --loglevel=info
    ;;
  *)
    exec "$@"
    ;;
esac
