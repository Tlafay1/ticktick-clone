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

## Releases & installation des clients (sans store)

Pousser un tag `v*` (ex. `git tag v1.1.0 && git push --tags`) déclenche
[release.yml](.github/workflows/release.yml) qui attache à la GitHub Release :

- **Windows** : l'installeur NSIS + `latest.yml`. L'app embarque
  **electron-updater** : elle vérifie les Releases GitHub au lancement (puis
  toutes les 4 h), télécharge en arrière-plan et installe au redémarrage —
  aucune action après la première installation.
- **Android** : l'APK. Signé release si les secrets de keystore sont
  configurés sur le repo (`ANDROID_KEYSTORE_BASE64` — keystore en base64,
  `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`),
  sinon signé debug (installable, mais garder ensuite le même mode de
  signature). Pour les mises à jour : installer l'APK par-dessus, ou pointer
  [Obtainium](https://github.com/ImranR98/Obtainium) sur ce repo pour être
  notifié et installer chaque release automatiquement.

Sur l'écran de connexion des clients embarqués, renseigner l'« URL du
serveur » self-hosted (mémorisée, préfixe API + WebSocket).

## Philosophie

Système simple et ouvert : pas de captcha, pas de rate-limiting, pas de
vérification d'email. L'API est entièrement documentée et accessible aux
développeurs.
