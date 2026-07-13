# Client Android (Capacitor)

L'app Android embarque le build web (`../web/dist`) dans un WebView Capacitor.
Plugins natifs : notifications locales, préférences, push FCM.

## Pré-requis

- Node 20+, Android Studio (SDK 34+), JDK 17.
- Un projet Firebase avec une app Android `com.ticktick.clone` :
  télécharger **`google-services.json`** et le placer dans
  [android/app/](android/app/) (non versionné).
  Côté serveur, le même projet alimente `FCM_SERVICE_ACCOUNT_JSON` (cf. `.env`).

## Build

```bash
cd mobile
npm install
npm run sync          # build web + copie dans android/ + sync plugins
npm run open          # ouvre Android Studio → Run ▶ ou Build > APK
```

Sous WSL : le SDK Android étant côté Windows, lancer `npm run sync` dans WSL
puis ouvrir `mobile/android` avec Android Studio **Windows** (le dossier est
accessible via `\\wsl$\…`), ou cloner le repo côté Windows pour le build.

## Release automatisée

Un tag `v*` sur le repo builde et attache l'APK à la GitHub Release
(cf. [release.yml](../.github/workflows/release.yml)) — signé release si la
keystore est en secrets, debug sinon. Pour les mises à jour sans store,
pointer [Obtainium](https://github.com/ImranR98/Obtainium) sur le repo.

## Connexion au serveur

L'app n'est pas servie par le backend : au premier lancement, renseigner
l'« URL du serveur » sur l'écran de connexion (ex. `https://ticktick.mondomaine.fr`).
Elle est mémorisée et préfixe toutes les requêtes API + WebSocket.

## Dev avec HMR

Décommenter `server.url` dans [capacitor.config.ts](capacitor.config.ts)
(`http://10.0.2.2:5173` = hôte vu depuis l'émulateur) puis `npx cap sync android`.

## Push FCM

Au premier lancement, l'app demande la permission de notification puis envoie
son jeton à `POST /api/push/fcm-token/`. Les rappels sont ensuite poussés par
le beat Celery (`dispatch_due_reminders` / `dispatch_habit_reminders`) via
FCM HTTP v1 — aucun fichier de credentials côté serveur, uniquement la
variable d'env `FCM_SERVICE_ACCOUNT_JSON`.
