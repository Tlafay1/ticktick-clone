# Agent de code local (Ollama GPU + aider)

Setup pour faire implémenter le projet par un modèle **local**, en semi-autonomie,
sur ce PC (Ryzen 7 9700X, **Radeon RX 9070 XT 16 Go**, WSL2/Ubuntu).

## Architecture

Le GPU AMD (ROCm) **n'est pas exposé à WSL** (`/dev/kfd` absent). Mais l'Ollama
**Windows** voit la carte (gfx1201, 15,8 Go de VRAM). On garde donc le LLM côté
Windows (GPU) et l'agent côté WSL (où vivent le repo, pytest, npm, Docker).

```
   WSL (Ubuntu)                              Windows
   ┌──────────────────────────┐  HTTP :11434 ┌──────────────────────────┐
   │ aider  ── édite le repo,   │ ───────────► │ Ollama 0.30.7            │
   │         lance le done-gate │              │  → GPU RX 9070 XT (ROCm) │
   └──────────────────────────┘              └──────────────────────────┘
```

- **Modèle** : `qwen3-coder:30b` (MoE 30B-A3B, Q4 ≈ 18 Go ; déborde un peu sur la
  RAM, reste rapide grâce au MoE).
- **Harness** : aider (conscient du repo + git, boucle test-driven sur le done-gate).

## Pré-requis Windows (déjà fait une fois)

`OLLAMA_HOST=0.0.0.0:11434` a été persisté (`setx`). Au prochain démarrage normal
d'Ollama (icône tray), il écoutera sur le réseau — accessible depuis WSL.

**Redémarrer Ollama exposé** (si besoin, depuis WSL) :
```bash
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
OLLAMA="C:\\Users\\tlcla\\AppData\\Local\\Programs\\Ollama\\ollama.exe"
$PS -NoProfile -Command "Get-Process 'ollama','ollama app' -ErrorAction SilentlyContinue | Stop-Process -Force"
$PS -NoProfile -Command "\$env:OLLAMA_HOST='0.0.0.0:11434'; Start-Process -FilePath '$OLLAMA' -ArgumentList 'serve' -WindowStyle Hidden"
```

**Tester le pont** depuis WSL (l'IP de l'hôte est la gateway par défaut) :
```bash
curl http://$(ip route show default | awk '{print $3}'):11434/api/version
```

## Lancer l'agent

```bash
./scripts/aider.sh                       # résout l'IP, vérifie le pont, lance aider
./scripts/aider.sh backend/apps/...      # en ajoutant des fichiers au contexte
```

`scripts/aider.sh` exporte `OLLAMA_API_BASE`, lance `aider --auto-test`. La config
(`.aider.conf.yml`) fixe le modèle et `test-cmd = ./scripts/done-gate.sh`
(pytest + build web + vitest). Avec `--auto-test`, aider relance le done-gate après
chaque édition et corrige jusqu'au vert.

### Boucle de travail conseillée (cf. CLAUDE.md)
Dans aider, on pilote jalon par jalon :
```
/ask  lis docs/requirements/ + le stub spec du module Mxx, puis explique le plan
# (aider répond) puis :
implémente Mxx : retire le skip du test, écris les assertions réelles, code jusqu'au done-gate vert
```
Donner peu à la fois (un module/un test), valider le diff, commit, recommencer.

## Réglages & perfs

- Contexte : `.aider.model.settings.yml` → `num_ctx: 16384`. Baisser à 8192 si lent.
- Suivre la charge GPU côté Windows : `rocm-smi` (PowerShell) pendant une génération.
- `OLLAMA_HOST` persistant : `setx` écrit dans le registre ; effectif au prochain
  lancement de l'app. L'IP gateway WSL peut changer après `wsl --shutdown` — le
  script la recalcule à chaque fois, rien à coder en dur.

## Attentes réalistes (lis ceci)

Un modèle local 30B + aider est bon pour des **tâches bien cadrées adossées à un
test** : un endpoint, un serializer, une règle métier, un composant Vue simple —
avec toi qui valides les diffs. Il **ne construira pas seul** le sync temps réel,
l'offline, le Gantt ou les widgets Kotlin : c'est une limite de capacité du modèle,
pas de la spec. Avance par petits incréments testés ; garde la main sur les morceaux
durs (ou réserve-les à un modèle plus fort). La spec (`docs/requirements/`,
`backend/spec/`, le done-gate) est justement là pour rendre les petites tâches
fiables et empêcher le faux « vert ».

## Dépannage

| Symptôme | Cause / fix |
|----------|-------------|
| `Ollama injoignable` | Ollama pas lancé exposé → section « Redémarrer Ollama exposé ». |
| Lenteur extrême | VRAM saturée → baisser `num_ctx`, fermer jeux/apps GPU, ou quant plus petit. |
| `connection refused` après reboot WSL | l'IP gateway a changé : `scripts/aider.sh` la recalcule, relancer simplement. |
| aider plante au démarrage (`audioop`) | `uv tool install aider-chat --with audioop-lts --force`. |
