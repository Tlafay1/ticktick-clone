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

# Paire VAPID (Web Push). Au choix :
uv run vapid --gen            # depuis backend/, écrit private_key.pem / public_key.pem
# ou en une ligne :
uv run python -c "from py_vapid import Vapid01; v=Vapid01(); v.generate_keys(); \
import base64; \
print('PUB', base64.urlsafe_b64encode(v.public_key.public_bytes_raw()).decode().rstrip('=')); \
print('PRIV', base64.urlsafe_b64encode(v.private_key.private_numbers().private_value.to_bytes(32,'big')).decode().rstrip('='))"
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

## 5. Journal intime → Obsidian (optionnel)

L'outil journal (API 0.3.0, [integration-ia.md](integration-ia.md)) écrit dans
la daily note du vault, synchronisé par le service `obsidian-sync` — le
**client headless officiel Obsidian Sync** (open beta, abonnement Sync requis),
100 % sans GUI. Sans les variables ci-dessous, le service reste inactif et
l'API journal répond 503 : le reste de la stack n'est pas affecté.

1. **Obtenir le token** (une fois, depuis n'importe quelle machine avec Docker,
   demande email + mot de passe + MFA Obsidian) :
   ```bash
   docker run --rm -it --entrypoint get-token \
     ghcr.io/belphemur/obsidian-headless-sync-docker:latest
   ```
2. Renseigner dans l'environnement Dokploy : `OBSIDIAN_AUTH_TOKEN`,
   `OBSIDIAN_VAULT_NAME` (nom exact, sensible à la casse),
   `OBSIDIAN_VAULT_PASSWORD` (seulement si chiffrement de bout en bout) et
   `OBSIDIAN_VAULT_PATH=/vault`.
3. Redéployer : `obsidian-sync` télécharge le vault dans le volume partagé
   `obsidian_vault`, puis le maintient à jour dans les deux sens.
4. **Daily notes** : la config du plugin natif (dossier, format, template) est
   lue dans `.obsidian/daily-notes.json` du vault. Vérifier que la config
   `.obsidian` fait partie de la sync ; sinon, renseigner `JOURNAL_DAILY_FOLDER`
   / `JOURNAL_DAILY_FORMAT` (tokens numériques `YYYY`, `MM`, `DD`…).
5. Test : `POST /api/journal/entries/` avec une clé d'API
   (voir [integration-ia.md](integration-ia.md)) → l'entrée apparaît sous
   `## Journal` de la daily note sur tous les appareils.

⚠️ La section `## Journal` est re-rendue en entier à chaque écriture de
l'agent : ne pas y éditer à la main (le reste de la note reste intouché).

## Test local de la stack prod

```bash
cp .env.example .env   # renseigner au minimum les secrets
docker compose -f docker-compose.prod.yml up --build
# front : http://localhost:8080   ·   API : http://localhost:8080/api/docs/
```
