# TickTick Clone

Clone self-hosted et mono-utilisateur de TickTick.

- **Backend** : Django 5 + Django REST Framework + Channels + Celery (`backend/`)
- **Web** : Vue 3 + TypeScript + Vite + Pinia (`web/`)
- **Mobile** : Capacitor — Android uniquement (`mobile/`)
- **Desktop** : Electron — Windows uniquement (`desktop/`)

## Démarrage rapide (dev)

```bash
# 1. Bases de données
docker compose up -d

# 2. Backend (http://localhost:8000)
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py runserver

# 3. Web (http://localhost:5173)
cd web
npm install
npm run dev
```

- API browsable : http://localhost:8000/api/
- Documentation OpenAPI (Swagger) : http://localhost:8000/api/docs/
- Admin Django : http://localhost:8000/admin/

## Tests

```bash
cd backend && uv run pytest
cd web && npm test
```

## Philosophie

Système simple et ouvert : pas de captcha, pas de rate-limiting, pas de
vérification d'email. L'API est entièrement documentée et accessible aux
développeurs.
