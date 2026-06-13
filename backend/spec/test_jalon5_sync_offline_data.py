"""Jalon 5 — Sync temps réel, offline, données (stubs).

Modules PRD : 12.1 (sync WebSocket + offline), 12.1 (export/import), 24
(import tiers, backup/restore), 1.1 (pièces jointes), 32 (annotation image),
33 (commentaires, déjà partiellement J1), 27.1 (historique de versions),
10.2 (recherche avancée + historique), 1.2 (archivage).
"""
import pytest

pytestmark = pytest.mark.spec
TODO = NotImplementedError


class TestM12RealtimeSync:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Sync temps réel (Channels)")

    def test_mutation_broadcasts_to_other_clients(self):
        """Une écriture est diffusée aux autres connexions du même utilisateur."""
        raise TODO

    def test_monotonic_seq_per_user(self):
        """Chaque mutation reçoit un `seq` croissant par utilisateur."""
        raise TODO

    def test_websocket_auth_via_jwt(self):
        """La connexion WebSocket s'authentifie avec le JWT."""
        raise TODO


class TestM12Offline:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Offline & file de mutations")

    def test_offline_mutations_queued_locally(self):
        """Hors-ligne, les mutations sont mises en file (UUID client, idempotent)."""
        raise TODO

    def test_queue_replayed_on_reconnect(self):
        """À la reconnexion, la file est rejouée vers le serveur."""
        raise TODO

    def test_last_write_wins_per_field_conflict(self):
        """Conflit résolu en last-write-wins par champ (horodatage)."""
        raise TODO


class TestM01Attachments:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Pièces jointes")

    def test_upload_file_and_image_with_preview(self):
        """Upload de fichiers/images (avec prévisualisation)."""
        raise TODO

    def test_voice_note_audio_recording(self):
        """Note vocale = simple enregistrement audio (sans transcript)."""
        raise TODO

    def test_max_constraints_and_ownership(self):
        """Les pièces jointes appartiennent à la tâche de l'utilisateur."""
        raise TODO


class TestM32ImageAnnotation:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Annotation d'image")

    def test_pen_shapes_text_overlay(self):
        """Éditeur d'image : stylo, formes, texte par-dessus l'image."""
        raise TODO

    def test_save_flattens_and_replaces_attachment(self):
        """Sauver aplatit les calques et remplace le fichier sans ré-upload externe."""
        raise TODO


class TestM27VersionHistory:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Historique de versions")

    def test_description_edits_logged_as_revisions(self):
        """Les éditions de la description sont historisées (ledger différentiel)."""
        raise TODO

    def test_restore_previous_revision(self):
        """On peut restaurer une version antérieure du texte."""
        raise TODO


class TestM12ExportImport:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Export/Import CSV & JSON")

    def test_export_full_data_csv_json(self):
        """Export complet des données en CSV et JSON."""
        raise TODO

    def test_import_rebuilds_database(self):
        """Import/restore reconstruit la base utilisateur."""
        raise TODO


class TestM24Migration:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Import tiers & backup")

    def test_generic_csv_importer(self):
        """Importeur CSV générique (couvre Todoist & co via leur export)."""
        raise TODO

    def test_backup_zip_covers_tasks_lists_priorities(self):
        """Le backup couvre tâches actives/archivées, listes, priorités, descriptions."""
        raise TODO


class TestM01Archive:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Archivage des tâches terminées")

    def test_completed_tasks_archived_off_active_load(self):
        """Les tâches terminées peuvent être archivées pour alléger les vues actives."""
        raise TODO


class TestM10AdvancedSearch:
    pytestmark = pytest.mark.skip(reason="Jalon 5 — Recherche avancée & historique")

    def test_filter_results_by_list_tag_date_status_attachments(self):
        """Filtres de recherche : liste, tag, date, statut, présence de pièces jointes."""
        raise TODO

    def test_search_history_recent_queries(self):
        """Historique des recherches récentes réutilisables."""
        raise TODO
