#!/usr/bin/env bash
# Lance aider (dans WSL) connecté à Ollama qui tourne sur le GPU côté Windows.
# L'IP de l'hôte Windows en mode NAT change parfois : on la résout dynamiquement.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HOST_IP="$(ip route show default | awk '{print $3}')"
export OLLAMA_API_BASE="http://${HOST_IP}:11434"

if ! curl -s --max-time 5 "${OLLAMA_API_BASE}/api/version" >/dev/null; then
  echo "❌ Ollama injoignable à ${OLLAMA_API_BASE}"
  echo "   Côté Windows, Ollama doit tourner avec OLLAMA_HOST=0.0.0.0:11434."
  echo "   Voir docs/local-agent-setup.md (section « Redémarrer Ollama exposé »)."
  exit 1
fi
echo "✓ Ollama (GPU Windows) : ${OLLAMA_API_BASE}"

cd "$ROOT"
# --auto-test : après chaque édition, aider lance le done-gate et corrige jusqu'au vert.
exec aider --auto-test "$@"
