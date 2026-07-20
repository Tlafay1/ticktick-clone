# Déploiement (self-hosted, Dokploy)

Stack de production : `docker-compose.prod.yml` — services `postgres`, `redis`,
`backend` (ASGI gunicorn+uvicorn), `worker` + `beat` (Celery, rappels), `web` (nginx
servant le SPA Vue et relayant `/api`, `/media`, `/static`, `/ws` vers le backend).

## Pré-requis serveur

- Dokploy installé (Traefik gère le domaine + TLS).
- Ressources mono-utilisateur : **2 vCPU / 2 Go RAM / 10 Go disque** (le build `vite`
  + `vue-tsc` est le pic mémoire ; le runtime tient sous ~800 Mo).

## 1. Générer les secrets

```bash
# Clé Django
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Paire VAPID (Web Push), depuis backend/ :
uv run vapid --gen            # écrit private_key.pem / public_key.pem
uv run python -c "
from cryptography.hazmat.primitives import serialization
import base64
with open('private_key.pem', 'rb') as f:
    priv = serialization.load_pem_private_key(f.read(), password=None)
pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
priv_val = priv.private_numbers().private_value.to_bytes(32, 'big')
print('VAPID_PUBLIC_KEY=' + base64.urlsafe_b64encode(pub).decode().rstrip('='))
print('VAPID_PRIVATE_KEY=' + base64.urlsafe_b64encode(priv_val).decode().rstrip('='))
"
rm private_key.pem public_key.pem
```

La clé publique VAPID est aussi exposée au front via `GET /api/push/public-key/`.

## 2. Variables d'environnement

Copier `.env.example` → `.env` et renseigner (voir commentaires). Dans Dokploy,
renseigner ces variables dans l'onglet *Environment* de l'application Compose.

## 3. Déployer

1. Dans Dokploy : **Create Application → Compose**, pointer sur ce dépôt + branche,
   fichier `docker-compose.prod.yml`.
2. Renseigner les variables d'environnement.
3. Associer le domaine au service `web` (port 80) ; Traefik émet le certificat TLS.
4. Déployer. Chaque `git push` sur la branche redéclenche un build + run automatique.

Les migrations s'appliquent automatiquement au démarrage du service `backend`
(`entrypoint.sh`). Le premier compte se crée via `POST /api/auth/register/`
(inscription ouverte, mono-utilisateur).

## 4. Vérifications post-déploiement

- `https://<domaine>/api/docs/` → Swagger accessible.
- Connexion au front, création d'une tâche.
- Activer les notifications dans les réglages → un rappel arrivé à échéance déclenche
  une notification Web Push (worker `beat` scrute toutes les minutes).

## Test local de la stack prod

```bash
cp .env.example .env   # renseigner au minimum les secrets
docker compose -f docker-compose.prod.yml up --build
# front : http://localhost:8080   ·   API : http://localhost:8080/api/docs/
```
