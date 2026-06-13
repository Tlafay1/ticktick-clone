#!/usr/bin/env bash
# Done-gate : un comportement n'est « fait » que si TOUT est vert.
# Utilisé par aider (--test-cmd) pour itérer jusqu'au vert, et à la main.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0

# pytest a besoin de Postgres : on le démarre si nécessaire.
if ! docker exec ticktick-clone-postgres-1 pg_isready -U ticktick >/dev/null 2>&1; then
  echo "→ Postgres absent, démarrage de docker compose…"
  (cd "$ROOT" && docker compose up -d >/dev/null 2>&1)
  for _ in $(seq 1 20); do
    docker exec ticktick-clone-postgres-1 pg_isready -U ticktick >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "===== backend : pytest ====="
(cd "$ROOT/backend" && uv run pytest -q) || fail=1

echo "===== web : build (typecheck + bundle) ====="
(cd "$ROOT/web" && npm run build) || fail=1

echo "===== web : vitest ====="
(cd "$ROOT/web" && npm test) || fail=1

if [ "$fail" -ne 0 ]; then
  echo "DONE-GATE : ÉCHEC"
  exit 1
fi
echo "DONE-GATE : OK ✓"
