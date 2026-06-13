#!/usr/bin/env bash
# Implémentation autonome (overnight) — jalons 2→5 + 8.
# Lance aider en boucle, un module par appel, sans interaction.
#
# Usage :
#   nohup ./scripts/overnight.sh > /tmp/overnight.log 2>&1 &
#   tail -f /tmp/overnight.log      ← suivre en direct
#
# Jalons 6 (Android) et 7 (Windows) sont exclus : natifs, impossibles à
# valider par pytest. À faire manuellement après les builds Capacitor/Electron.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Vérification Ollama ──────────────────────────────────────────────────────
HOST_IP="$(ip route show default | awk '{print $3}')"
export OLLAMA_API_BASE="http://${HOST_IP}:11434"
if ! curl -s --max-time 5 "${OLLAMA_API_BASE}/api/version" >/dev/null; then
  echo "❌  Ollama injoignable à ${OLLAMA_API_BASE}"
  echo "    Voir docs/local-agent-setup.md → section « Redémarrer Ollama exposé »."
  exit 1
fi
echo "✓  Ollama GPU : ${OLLAMA_API_BASE}"
cd "$ROOT"   # aider lit .aider.conf.yml depuis le cwd

# ── Logs ─────────────────────────────────────────────────────────────────────
LOG_DIR="$ROOT/scripts/logs"
mkdir -p "$LOG_DIR"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
SUMMARY="$LOG_DIR/overnight-${RUN_ID}-summary.txt"
echo "Démarré $(date '+%Y-%m-%d %H:%M:%S')" > "$SUMMARY"

pass=0; fail=0

# ── Fonction principale ───────────────────────────────────────────────────────
# run_module SPEC_FILE CLASS_NAME "req1.md req2.md" "Description courte"
run_module() {
  local spec_file="$1"
  local class_name="$2"
  local req_files="$3"
  local description="$4"

  local log_file="$LOG_DIR/${RUN_ID}-${class_name}.log"

  echo ""
  echo "━━━  $(date '+%H:%M:%S')  ${class_name}  (${description})  ━━━"

  # Construire la liste des fichiers requirements
  # Construire les args --read pour les fichiers requirements (lecture seule = moins de tokens)
  local req_read_args=()
  local req_list=""
  for f in $req_files; do
    local fpath="$ROOT/docs/requirements/$f"
    req_read_args+=(--read "$fpath")
    req_list+="$fpath "
  done

  local msg
  msg="Read the following files to understand the full requirement:
${req_list}
Also read: $ROOT/backend/spec/${spec_file}

Your task: implement the spec class ${class_name}.

Steps (follow strictly):
1. Open $ROOT/backend/spec/${spec_file}.
2. Find class ${class_name}. Remove its \`pytestmark = pytest.mark.skip(...)\` line.
3. Replace every \`raise TODO\` in that class with a real pytest assertion.
   Each test docstring is the acceptance contract — honour it exactly.
4. Implement or extend whatever Django models, migrations, serializers,
   viewsets, and urls.py entries are required to make those assertions pass.
   Add to existing apps (accounts/projects/tasks/tags/…) rather than creating
   new ones unless unavoidable.
5. After every file edit, run \`./scripts/done-gate.sh\` and fix any failures.
   Iterate until the gate is green: pytest 0 errors, build ok, vitest ok.
6. Do NOT re-add skip or xfail markers on this class.
7. Commit when done (git commit -m \"feat: implement ${class_name}\")."

  local exit_code=0
  aider \
    --yes-always \
    --auto-test \
    --no-check-update \
    --no-suggest-shell-commands \
    "${req_read_args[@]}" \
    --message "$msg" \
    "$ROOT/backend/spec/${spec_file}" \
    >"$log_file" 2>&1 || exit_code=$?

  # Vérification réelle : le skip doit avoir été retiré de la classe cible.
  # Un aider qui n'a rien fait sort avec exit 0 (done-gate OK = tous skippés),
  # mais le skip encore présent trahit l'absence de vrai travail.
  local skip_still_present=0
  if grep -A1 "^class ${class_name}" "$ROOT/backend/spec/${spec_file}" \
       | grep -q "pytest.mark.skip"; then
    skip_still_present=1
  fi

  if [[ $exit_code -eq 0 && $skip_still_present -eq 0 ]]; then
    echo "    ✓  PASS  →  $log_file"
    echo "PASS  ${class_name}" >> "$SUMMARY"
    pass=$((pass + 1))
  else
    local reason="exit ${exit_code}"
    [[ $skip_still_present -eq 1 ]] && reason="skip non retiré (pas de vrai travail)"
    echo "    ✗  FAIL (${reason})  →  $log_file"
    echo "FAIL  ${class_name}  (${reason})" >> "$SUMMARY"
    fail=$((fail + 1))
  fi
}

# ════════════════════════════════════════════════════════════════════════════
# JALON 2 — Organisation avancée
# Modules : 2.1, 2.3, 3, 1 (récurrence/rappels), 15, 25.3, 23, 24.1, 26.2, 20.3
# ════════════════════════════════════════════════════════════════════════════
J2=test_jalon2_organization.py

run_module "$J2" TestM02Folders \
  "modules-01-12.md" \
  "Dossiers de listes (ProjectGroup)"

run_module "$J2" TestM02ListCustomization \
  "modules-01-12.md" \
  "Personnalisation des listes (couleur, icône, view_mode, archive)"

run_module "$J2" TestM02CustomSmartListsFilterEngine \
  "modules-01-12.md" \
  "Smart lists custom — moteur de filtre booléen AND/OR"

run_module "$J2" TestM03NestedTags \
  "modules-01-12.md" \
  "Tags hiérarchiques + couleurs + merge"

run_module "$J2" TestM01Recurrence \
  "modules-01-12.md" \
  "Récurrence RRULE complète (presets + custom + after-completion)"

run_module "$J2" TestM01RemindersAndM15AnnoyingAlert \
  "modules-01-12.md modules-13-18.md" \
  "Rappels multiples + Annoying Alert + snooze"

run_module "$J2" TestM25DefaultCreationPresets \
  "modules-19-35.md" \
  "Paramètres de création par défaut (projet, priorité, rappels)"

run_module "$J2" TestM23Templates \
  "modules-19-35.md" \
  "Templates tâche et liste"

run_module "$J2" TestM24BatchPaste \
  "modules-19-35.md" \
  "Batch copy-paste import"

run_module "$J2" TestM20TaskLinkResolution \
  "modules-19-35.md" \
  "Deep links tâche (app://task/id)"

run_module "$J2" TestM01ActivityLog \
  "modules-01-12.md" \
  "Journal d'activité des tâches"

# ════════════════════════════════════════════════════════════════════════════
# JALON 3 — Calendrier, Kanban, Timeline, Eisenhower
# Modules : 4, 16, 5, 13, 19, 30
# ════════════════════════════════════════════════════════════════════════════
J3=test_jalon3_calendar_boards.py

run_module "$J3" TestM04CalendarViews \
  "modules-01-12.md" \
  "Vues calendrier jour/3j/semaine/mois/agenda"

run_module "$J3" TestM04TimeBlocking \
  "modules-01-12.md" \
  "Drag-to-schedule + time blocking"

run_module "$J3" TestM16Duration \
  "modules-13-18.md" \
  "Durée de tâche (heure début + heure fin)"

run_module "$J3" TestM04IcsSubscription \
  "modules-01-12.md" \
  "Abonnements ICS read-only"

run_module "$J3" TestM05Kanban \
  "modules-01-12.md" \
  "Kanban (sections/colonnes, réordonner, replier)"

run_module "$J3" TestM05Timeline \
  "modules-01-12.md" \
  "Timeline/Gantt (barres, resize, déplacement)"

run_module "$J3" TestM13Eisenhower \
  "modules-13-18.md" \
  "Matrice d'Eisenhower (4 quadrants, drag entre quadrants)"

run_module "$J3" TestM19YearViewHeatmap \
  "modules-19-35.md" \
  "Vue annuelle + heatmap de productivité"

run_module "$J3" TestM19ModernClassicCalendar \
  "modules-19-35.md" \
  "Bascule calendrier moderne / classique"

run_module "$J3" TestM30TimelineSlotHiding \
  "modules-19-35.md" \
  "Masquage de créneaux horaires (sliders)"

# ════════════════════════════════════════════════════════════════════════════
# JALON 4 — Habitudes, Focus, Countdown, Stats
# Modules : 6, 28, 21, 7, 29, 18, 17, 12, 26
# ════════════════════════════════════════════════════════════════════════════
J4=test_jalon4_habits_focus_stats.py

run_module "$J4" TestM06HabitConfig \
  "modules-01-12.md" \
  "Configuration des habitudes (fréquences, objectifs, unités)"

run_module "$J4" TestM28HabitCheckInModes \
  "modules-19-35.md" \
  "Modes de check-in habitude (auto/manuel/binaire)"

run_module "$J4" TestM21HabitMultiLog \
  "modules-19-35.md" \
  "Multi-check-in par jour"

run_module "$J4" TestM06HabitTrackingStats \
  "modules-01-12.md" \
  "Stats habitudes (streaks, calendrier, taux de complétion)"

run_module "$J4" TestM07Focus \
  "modules-01-12.md" \
  "Focus Pomodoro + chrono (durées custom, auto-start, sons)"

run_module "$J4" TestM21FocusEstimation \
  "modules-19-35.md" \
  "Estimation pomos prévisionnelle vs réelle"

run_module "$J4" TestM07FocusStats \
  "modules-01-12.md" \
  "Statistiques focus (camemberts, tendances)"

run_module "$J4" TestM29WebTabTimer \
  "modules-19-35.md" \
  "Timer dans le titre d'onglet navigateur"

run_module "$J4" TestM18Countdown \
  "modules-13-18.md" \
  "Countdown jours restants (cartes anniversaires/échéances)"

run_module "$J4" TestM17Summary \
  "modules-13-18.md" \
  "Page Summary / statistiques (score, distribution, historique)"

run_module "$J4" TestM12Gamification \
  "modules-01-12.md" \
  "Score de productivité + niveaux + badges"

run_module "$J4" TestM26DailyReview \
  "modules-19-35.md" \
  "Daily review planifié (Celery beat, notification quotidienne)"

# ════════════════════════════════════════════════════════════════════════════
# JALON 5 — Sync temps réel, offline, données
# Modules : 12 (sync/offline/export), 1 (PJ), 32, 27, 24.2, 10
# ════════════════════════════════════════════════════════════════════════════
J5=test_jalon5_sync_offline_data.py

run_module "$J5" TestM12RealtimeSync \
  "modules-01-12.md" \
  "WebSocket Channels sync temps réel (seq, mutations idempotentes)"

run_module "$J5" TestM12Offline \
  "modules-01-12.md" \
  "File offline + résolution de conflits last-write-wins"

run_module "$J5" TestM01Attachments \
  "modules-01-12.md" \
  "Pièces jointes (fichiers, images, notes vocales audio)"

run_module "$J5" TestM32ImageAnnotation \
  "modules-19-35.md" \
  "Annotation image (canvas)"

run_module "$J5" TestM27VersionHistory \
  "modules-19-35.md" \
  "Historique de versions de description + restauration"

run_module "$J5" TestM12ExportImport \
  "modules-01-12.md" \
  "Export/import CSV & JSON + backup/restore"

run_module "$J5" TestM24Migration \
  "modules-19-35.md" \
  "Import générique CSV (Todoist, Ticktick, etc.)"

run_module "$J5" TestM01Archive \
  "modules-01-12.md" \
  "Archivage des tâches terminées"

run_module "$J5" TestM10AdvancedSearch \
  "modules-01-12.md" \
  "Recherche avancée + filtres + historique de recherche"

# ════════════════════════════════════════════════════════════════════════════
# JALON 8 — Finitions UX (parties testables côté backend)
# Modules : 12 (thèmes), 19 (fonds), 31 (Tier 3)
# ════════════════════════════════════════════════════════════════════════════
J8=test_jalon8_polish.py

run_module "$J8" TestM12ThemesAndPrefs \
  "modules-19-35.md" \
  "Thèmes clair/sombre/auto + presets de couleurs (persistés en settings)"

run_module "$J8" TestM19ListBackgrounds \
  "modules-19-35.md" \
  "Fonds personnalisés par liste"

run_module "$J8" TestM31Tier3MarkdownPolish \
  "modules-19-35.md" \
  "Polish Tier 3 : checkboxes markdown dans la description"

# ════════════════════════════════════════════════════════════════════════════
# NOTE : Jalons 6 (Android) et 7 (Windows) exclus — natifs, hors pytest.
# Les implémenter manuellement après les builds Capacitor / Electron.
# ════════════════════════════════════════════════════════════════════════════

# ── Résumé final ─────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  Résumé overnight  —  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  ✓ Passés  : ${pass}"
echo "  ✗ Échoués : ${fail}"
echo "  Logs      : ${LOG_DIR}/${RUN_ID}-*.log"
echo "  Résumé    : ${SUMMARY}"
echo "══════════════════════════════════════════════════"
{
  echo ""
  echo "Terminé $(date '+%Y-%m-%d %H:%M:%S')  —  pass=${pass} fail=${fail}"
} >> "$SUMMARY"
